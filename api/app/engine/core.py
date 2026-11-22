"""TraceEngine implementation. Methods are filled in step by step."""
from __future__ import annotations

from pathlib import Path

from app.contracts import (
    ClosureReport, Finding, Link, NCStatus, Recommendation, Role, Severity,
    Verdict, VerificationTask,
)
from app.engine.clock import Clock, SystemClock
from app.engine.features import FeatureIndex, FrozenIdf
from app.engine.graph import DEFAULT_MAX_HOPS, build_graph
from app.engine.scoring import FrozenWeights, LinkScorer, load_weights
from app.engine.store import NCStore, is_unresolved
from app.engine.types import Graph

IDF_PATH = Path(__file__).with_name("idf.json")
LINK_MIN = 0.70  # a link counts as "connected" at this score or higher
class TraceEngineImpl:
    def __init__(
        self, store: NCStore, clock: Clock | None = None, weights: FrozenWeights | None = None
    ) -> None:
        self.store = store
        self.clock = clock or SystemClock()
        self._weights = weights
        self._index: FeatureIndex | None = None

    def refresh_index(self) -> None:
        """Rebuild text vectors using the frozen DEV IDF when required."""
        if self._weights is None:
            self._weights = load_weights()

        expected_hash = self._weights.meta.get("dev_idf_sha256")

        if expected_hash:
            if not IDF_PATH.exists():
                raise FileNotFoundError(
                    f"Frozen DEV IDF not found: {IDF_PATH}"
                )

            idf = FrozenIdf.load(IDF_PATH)

            if idf.digest != expected_hash:
                raise ValueError(
                    "Frozen IDF hash does not match the model weights."
                )

            self._index = FeatureIndex(self.store.list_ncs(), idf=idf)
        else:
            self._index = FeatureIndex(self.store.list_ncs())

    def _scorer(self) -> LinkScorer:
        if self._weights is None:
            self._weights = load_weights()

        if self._index is None:
            self.refresh_index()

        return LinkScorer(
            self._index,
            self._weights,
            self.store.get_weight_deltas(),
        )
    def index_nc(self, nc_id: str) -> list[Link]:
        """Compute and store all links for one NC (call on NC create/update)."""
        nc = self.store.get_nc(nc_id)
        if nc is None:
            raise KeyError(nc_id)
        if self._index is None:
            self.refresh_index()
        else:
            self._index.upsert(nc)
        return self.store.save_links(nc_id, self._scorer().related(nc_id))

    def index_all(self) -> int:
        """Compute and store links for every NC. Returns the number of unique links."""
        self.refresh_index()
        grouped = self._scorer().all_links()
        for nc_id, links in grouped.items():
            self.store.save_links(nc_id, links)
        return sum(len(v) for v in grouped.values()) // 2

    def find_related(self, nc_id: str) -> list[Link]:
        if self.store.get_nc(nc_id) is None:
            raise KeyError(nc_id)
        return self.store.get_links(nc_id)

    def get_graph(self, nc_id: str, max_hops: int = DEFAULT_MAX_HOPS) -> Graph:
        """Linked NCs, failure paths and footprint around one NC (KeyError if unknown)."""
        return build_graph(self.store, nc_id, self.clock.now(), max_hops)

    def simulate_closure(self, nc_id: str) -> ClosureReport:
        """Rules R1-R7 over stored links and records. Deterministic and explainable.

        Verdict thresholds:
          HOLD   = any critical finding, OR R1 (unresolved connected NC) together
                   with R2 (fix scope too narrow) or R3 (recurrence after closure).
          VERIFY = any other finding.
          CLEAR  = no findings.
        If no action scope is stored, the fix is assumed to cover only the NC's own line.
        """
        nc = self.store.get_nc(nc_id)
        if nc is None:
            raise KeyError(nc_id)
        today = self.clock.now().date()

        links = [l for l in self.store.get_links(nc_id) if l.score >= LINK_MIN]
        others = []
        for l in links:
            o = self.store.get_nc(l.b if l.a == nc_id else l.a)
            if o is not None:
                others.append(o)
        unresolved = [o for o in others if is_unresolved(o)]
        same_cause = [o for o in others if o.root_cause_category == nc.root_cause_category]
        actions = self.store.get_actions(nc_id)
        evidence = self.store.get_evidence(nc_id)
        findings: list[Finding] = []

        def add(rule: str, sev: Severity, msg: str, refs: list[str]) -> None:
            findings.append(Finding(rule=rule, severity=sev, message=msg, evidence_refs=refs))

        # R1 unresolved connected NC
        if unresolved:
            sev = Severity.critical if any(o.severity == Severity.critical for o in unresolved) else Severity.major
            add("R1", sev, f"{len(unresolved)} connected NC(s) are still unresolved: "
                f"{', '.join(o.id for o in unresolved)}.", [o.id for o in unresolved])

        # R2 action scope narrower than affected scope
        scope = self.store.get_action_scope_lines(nc_id)
        covered = set(scope) if scope is not None else {nc.line}
        affected = {nc.line} | {o.line for o in unresolved}
        missing = sorted(x for x in affected - covered if x)
        if missing:
            add("R2", Severity.major, f"The fix covers {', '.join(sorted(x for x in covered if x)) or 'no line'} "
                f"but the problem also exists on {', '.join(missing)}.", [o.id for o in unresolved])

        # R3 same root cause recurred after a prior closure
        recur = [o for o in same_cause if o.closed_at is not None and nc.raised_at > o.closed_at]
        if recur:
            add("R3", Severity.major, f"Root cause {nc.root_cause_category} returned after earlier closure of "
                f"{', '.join(o.id for o in recur)}.", [o.id for o in recur])

        # R4 symptom-only action
        if not actions:
            add("R4", Severity.major, "No action plan is recorded.", [nc.id])
        elif not any(a.preventive_action for a in actions):
            add("R4", Severity.minor, "Only a corrective action exists. There is no preventive action.",
                [f"action:{a.id}" for a in actions])

        # R5 weak evidence
        if not evidence:
            add("R5", Severity.major, "No evidence was uploaded.", [nc.id])
        elif all(e.uploaded_at < nc.raised_at for e in evidence):
            add("R5", Severity.minor, "All evidence is older than the NC.", [f"evidence:{e.id}" for e in evidence])
        elif not any(e.has_before_after for e in evidence):
            add("R5", Severity.minor, "Evidence has no before/after comparison.", [f"evidence:{e.id}" for e in evidence])

        # R6 overdue sibling actions
        overdue = [o.id for o in unresolved
                   if any(a.target_date < today for a in self.store.get_actions(o.id))]
        if overdue:
            add("R6", Severity.minor, f"Connected NC(s) have overdue actions: {', '.join(overdue)}.", overdue)

        # R7 similar action failed before
        failed = [o.id for o in same_cause
                  if o.status == NCStatus.REOPENED
                  or any(not v.accepted for v in self.store.get_verifications(o.id))]
        if failed:
            add("R7", Severity.minor, f"Earlier NC(s) with the same root cause had a failed fix: "
                f"{', '.join(failed)}.", failed)

        rules = {f.rule for f in findings}
        if any(f.severity == Severity.critical for f in findings) or ("R1" in rules and rules & {"R2", "R3"}):
            verdict = Verdict.HOLD
        elif findings:
            verdict = Verdict.VERIFY
        else:
            verdict = Verdict.CLEAR

        # Verification tasks, created from the findings
        tasks: list[VerificationTask] = []
        lines = sorted({x for x in ({nc.line} | {o.line for o in unresolved}) if x})
        where = " and ".join(lines) if lines else "the affected lines"
        if rules & {"R1", "R2"}:
            what = "Check tool-life counters" if nc.root_cause_category == "TOOL_LIFE" else "Check the root-cause controls"
            tasks.append(VerificationTask(nc_id=nc_id, title=f"{what} on {where}",
                                          priority=1, suggested_owner_role=Role.auditor))
        if rules & {"R1", "R3", "R5"}:
            tasks.append(VerificationTask(nc_id=nc_id, title="Sample 30 pcs from the last 3 lots",
                                          priority=2, suggested_owner_role=Role.auditor))
        if rules & {"R2", "R4", "R7"}:
            tasks.append(VerificationTask(nc_id=nc_id, title="Update the control plan and add a preventive action",
                                          priority=3, suggested_owner_role=Role.auditee))

        return ClosureReport(nc_id=nc_id, verdict=verdict, findings=findings, links=links,
                             tasks=tasks, generated_at=self.clock.now())

    def plan_risk(self, month: str) -> list[Recommendation]:
        raise NotImplementedError("Step 11: risk-adaptive planner")

    def record_feedback(self, link_id: int, confirmed: bool) -> None:
        raise NotImplementedError("Step 11: learning loop")