"""Deterministic synthetic NC history (SYNTHETIC demo data, fixed seed).

generate(seed) returns contract objects plus a SEPARATE ground-truth dict.
The engine never sees ground truth; only eval/ and tests do.
Run:  python -m seed.generate --seed 42 --out seed/out
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

_API = Path(__file__).resolve().parents[1] / "api"
if str(_API) not in sys.path:
    sys.path.insert(0, str(_API))

from app.contracts import (
    NC,
    ActionPlan,
    AuditType,
    Evidence,
    NCStatus,
    Severity,
    Verification,
)
from app.engine import taxonomy as tx

from seed.golden import AS_OF, build_golden

SEED_DEFAULT = 42
N_TOTAL = 600
N_GOLDEN_NCS = 5
N_CLUSTERS = 20  # includes golden cluster C00
N_DECOYS = 88    # generated; golden.py adds 2 more
WINDOW_START = datetime(2025, 12, 1, 8, 0)
WINDOW_END = AS_OF - timedelta(days=3)
RESERVED_IDS = {361, 377, 390, 401, 408, 412}

# Placeholder user ids (align with Ishwarya's users seed)
AUDITORS = [101, 102, 103]
AUDITEES_BY_DEPT = {1: [204], 2: [201, 202], 3: [203], 4: [205], 5: [206], 6: [207], 7: [208]}

PART_NAME = {
    "Brake Drum": "brake drum", "Brake Disc": "brake disc", "Wheel Hub": "wheel hub",
    "Steering Knuckle": "steering knuckle", "Axle Shaft": "axle shaft", "Flywheel": "flywheel",
}
FEATURES = ["bore", "flange", "outer edge", "mounting face", "seat", "hub", "keyway", "spline", "web section"]
AUDITS = ["audit", "line check", "patrol audit", "final check"]
PROCESS_PREFIX = {
    "Casting": "CA", "CNC Turning": "CT", "Bore Machining": "BM", "Deburring": "DB",
    "Grinding": "GR", "Heat Treatment": "HT", "Surface Coating": "SC",
    "Assembly": "AS", "Final Inspection": "GA",
}

CONCEPT_DEFECT = {
    "burr": "DEF-BURR", "dimension": "DEF-DIM", "crack": "DEF-CRACK", "porosity": "DEF-POROS",
    "hardness": "DEF-HARD", "finish": "DEF-FINISH", "runout": "DEF-RUNOUT",
    "coating": "DEF-COAT", "damage": "DEF-DAMAGE",
}
CONCEPT_ROOT_CAUSES = {
    "burr": ["TOOL_LIFE", "MACHINE_SETTING", "METHOD", "OPERATOR", "FIXTURE", "MAINTENANCE", "MATERIAL"],
    "dimension": ["MACHINE_SETTING", "MEASUREMENT", "FIXTURE", "TOOL_LIFE", "MATERIAL", "MAINTENANCE", "OPERATOR"],
    "crack": ["MATERIAL", "HEAT_TREAT", "METHOD", "ENVIRONMENT", "MACHINE_SETTING", "OPERATOR"],
    "porosity": ["MATERIAL", "METHOD", "MACHINE_SETTING", "MAINTENANCE", "ENVIRONMENT"],
    "hardness": ["HEAT_TREAT", "MACHINE_SETTING", "MAINTENANCE", "METHOD", "MATERIAL", "MEASUREMENT"],
    "finish": ["TOOL_LIFE", "MACHINE_SETTING", "MAINTENANCE", "FIXTURE", "METHOD", "OPERATOR"],
    "runout": ["FIXTURE", "MACHINE_SETTING", "MAINTENANCE", "MEASUREMENT", "TOOL_LIFE", "METHOD"],
    "coating": ["MATERIAL", "METHOD", "ENVIRONMENT", "MACHINE_SETTING", "OPERATOR", "MAINTENANCE"],
    "damage": ["OPERATOR", "METHOD", "ENVIRONMENT", "FIXTURE", "MAINTENANCE"],
}
CONCEPT_PROCESSES = {
    "burr": ["Bore Machining", "CNC Turning", "Deburring", "Grinding"],
    "dimension": ["CNC Turning", "Bore Machining", "Grinding", "Final Inspection"],
    "crack": ["Casting", "Heat Treatment", "Grinding", "Assembly"],
    "porosity": ["Casting"],
    "hardness": ["Heat Treatment", "Final Inspection"],
    "finish": ["CNC Turning", "Grinding", "Bore Machining", "Deburring"],
    "runout": ["CNC Turning", "Bore Machining", "Assembly", "Final Inspection"],
    "coating": ["Surface Coating", "Final Inspection"],
    "damage": ["Assembly", "Final Inspection", "Deburring", "Surface Coating"],
}

# Five wordings per concept; some use glossary phrases, some deliberately do not.
TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "burr": [
        ("Burr on {part} {feature}, {line}", "Burr observed on {part} {feature} after {process_l} at {line}."),
        ("Sharp edge found on {part}, {line}", "Sharp edge on machined {feature} noted during {audit} at {line}; operator reported snagging."),
        ("Flash left on {part} {feature}", "Flash not removed from {feature} of {part}, {line} {process_l}."),
        ("Edge not broken on {part}", "Machined edge on {feature} not properly broken, rough lip felt by hand, {line}."),
        ("Handling cut risk: {part} edge", "Edge condition on {part} {feature} could cut hands during handling, {line}."),
    ],
    "dimension": [
        ("{part} {feature} out of tolerance, {line}", "Measured {feature} on {part} out of tolerance at {line} {process_l}."),
        ("Oversize {feature} on {part}", "Oversize condition found on {feature} of {part}; gauge no-go entered freely, {line}."),
        ("OOT dimension, {part}, {line}", "OOT reading on {feature} during {audit}; sample parts rejected, {line}."),
        ("Undersize {feature}, {part}", "Undersize {feature} on {part} at {line}; dimension deviation vs drawing."),
        ("{part} fit problem at check", "Mating parts did not fit {feature} of {part} properly, size looked off, {line}."),
    ],
    "crack": [
        ("Crack on {part} {feature}, {line}", "Crack visible on {feature} of {part} during {audit}, {line}."),
        ("Hairline crack found on {part}", "Hairline crack detected on {part} {feature} by dye penetrant check, {line}."),
        ("Cracking after processing: {part}", "{part} showed cracking near {feature} after {process_l}, {line}."),
        ("Fracture at {feature}, {part}", "Fracture at {feature} of {part} found on sampling, {line}."),
        ("Part split on test, {part}", "{part} split along {feature} during destructive test, lot held at {line}."),
    ],
    "porosity": [
        ("Porosity in {part} casting, {line}", "Porosity found on cut section of {part} near {feature}, {line}."),
        ("Blow hole on {part} {feature}", "Blow hole exposed on {feature} after machining, {part}, {line}."),
        ("Pinholes on machined face, {part}", "Pinhole defects on machined {feature} of {part}, {line}."),
        ("Shrinkage cavity, {part}", "Shrinkage cavity seen in {feature} of {part} during X-ray sampling."),
        ("Gas defects in casting lot", "Gas holes seen in {part} castings at {feature}, {line}; lot leaking on pressure test."),
    ],
    "hardness": [
        ("Low hardness on {part}, {line}", "Hardness below spec measured on {part} {feature}, {line}."),
        ("Soft spot on {part} {feature}", "Soft spot found at {feature} of {part} during hardness survey."),
        ("Hardness deviation, {part} lot", "Hardness deviation across {part} lot at {line}; some pieces under hardened."),
        ("Case depth shortfall, {part}", "Case depth lower than required on {part} {feature}, {line}."),
        ("Hardness test failed, {part}", "Hardness reading failed acceptance at {line} on {part}, retest requested."),
    ],
    "finish": [
        ("Rough surface on {part} {feature}, {line}", "Surface roughness above limit on {feature} of {part}, {line}."),
        ("Chatter marks on {part}", "Chatter marks visible on {feature} of {part} after {process_l}, {line}."),
        ("Scoring on {part} {feature}", "Scoring and scratches on {feature} of {part}, {line}."),
        ("Poor finish, {part} {feature}", "Poor finish on {feature} noted at {audit}; tool marks too deep, {line}."),
        ("Surface not smooth: {part}", "{feature} of {part} feels coarse, not smooth as per standard, {line}."),
    ],
    "runout": [
        ("Runout on {part}, {line}", "Runout beyond limit on {feature} of {part} measured at {line}."),
        ("{part} out of round", "Out of round condition on {feature}, {part}, {line}."),
        ("Wobble when mounted, {part}", "{part} showed wobble on test mandrel; eccentricity at {feature}, {line}."),
        ("Ovality on {feature}, {part}", "Ovality found on {feature} of {part} after {process_l}."),
        ("Vibration complaint, {part}", "Vibration noted on test rig for {part}; suspected {feature} geometry, {line}."),
    ],
    "coating": [
        ("Coating peel on {part}, {line}", "Coating peel on {feature} of {part}, poor adhesion, {line}."),
        ("Paint flaking on {part} {feature}", "Paint flaking on {feature} found at {audit}, {line}."),
        ("Uneven coating thickness, {part}", "Uneven coating on {part} {feature}; thickness varies across batch, {line}."),
        ("Bare patches on {part}", "Bare metal patches left on {feature} of {part} after {process_l}."),
        ("Finish colour mismatch, {part}", "Coating colour and gloss not matching master on {part}, {line}."),
    ],
    "damage": [
        ("Handling damage on {part}, {line}", "Dents and nicks on {feature} of {part} from handling at {line}."),
        ("Transit damage on {part} {feature}", "Scratches on {feature} caused during transfer between stations, {part}."),
        ("Dent found on {part}", "Dent on {feature} of {part} found at {audit}; bins not padded, {line}."),
        ("Parts stacked without separators", "{part} stacked directly, contact marks on {feature}, {line}."),
        ("Damaged {part} in WIP area", "Damage on {feature} of {part} in WIP storage, {line}."),
    ],
}
CAUSE_HINTS = {
    "TOOL_LIFE": ["Cutting insert worn beyond limit.", "No tool-life tracking in place.", "Tool change interval not defined.", "Blunt tool left running past due change."],
    "MACHINE_SETTING": ["Feed rate drifted after setup change.", "Machine parameter not as per setup sheet.", "Offsets changed without record.", "Spindle speed set wrongly after changeover."],
    "MATERIAL": ["Incoming material batch varied.", "Supplier lot hardness inconsistent.", "Raw material certificate not matching.", "Billet quality suspected."],
    "METHOD": ["Work instruction missing a step.", "Procedure not followed as written.", "SOP unclear for this operation.", "Method sheet outdated."],
    "MEASUREMENT": ["Gauge out of calibration.", "Measurement variation between shifts.", "Instrument drift suspected.", "Unverified gauge in use."],
    "OPERATOR": ["Operator not trained on this step.", "Skill gap on night shift.", "New operator without sign-off.", "Operator skipped check."],
    "FIXTURE": ["Fixture locating pad worn.", "Jig misaligned after repair.", "Clamping not repeatable.", "Fixture wear not checked."],
    "HEAT_TREAT": ["Furnace cycle deviated from recipe.", "Quench delay observed.", "Temperature profile off.", "Soak time shortened."],
    "MAINTENANCE": ["Preventive maintenance overdue.", "Machine PM missed last month.", "Lubrication schedule not followed.", "Spindle bearing wear suspected."],
    "ENVIRONMENT": ["Humidity high in shop.", "Parts left uncovered overnight.", "Storage area dusty.", "Transport trolley rough."],
}
SYMPTOM_ACTIONS = [
    "Replaced the affected tool and reworked the lot.",
    "Reworked rejected parts and re-inspected the lot.",
    "Cleaned the area and sorted suspect parts.",
    "Reset machine settings and re-inspected 100% of the lot.",
    "Replaced the worn part and deburred affected pieces.",
    "Retouched defect pieces and issued a verbal reminder.",
]
SYSTEMIC_ACTIONS = {
    "TOOL_LIFE": "Define tool-life limit, add tool-life counter and update control plan.",
    "MACHINE_SETTING": "Lock machine parameters, add setup verification checklist and update control plan.",
    "MATERIAL": "Add incoming inspection check and agree material spec with supplier.",
    "METHOD": "Revise work instruction, train operators and update control plan.",
    "MEASUREMENT": "Add gauge calibration schedule and R&R study.",
    "OPERATOR": "Standardise training matrix and add skill sign-off before solo work.",
    "FIXTURE": "Add fixture wear check to PM and replace on defined interval.",
    "HEAT_TREAT": "Add furnace recipe verification and recorder review every batch.",
    "MAINTENANCE": "Update PM plan with interval and add overdue alert.",
    "ENVIRONMENT": "Introduce covered storage, padded bins and housekeeping audit.",
}
ACCEPT_COMMENTS = [
    "Corrective action verified on shop floor.", "Evidence reviewed; parts sampled OK.",
    "Action implemented as planned.", "Checked with owner; acceptable.",
]
REJECT_COMMENTS = [
    "Evidence insufficient: no before/after record.", "Action does not address the root cause.",
    "Sample size too small; resubmit.",
]
ABBREV = {"machine": "m/c", "inspection": "insp.", "operator": "opr", "measured": "meas."}

OPEN_STATES = ["ASSIGNED", "ACTION_PLANNED", "IN_PROGRESS", "IN_PROGRESS", "EVIDENCE_SUBMITTED", "REJECTED"]
PENDING_STATES = ["AUDITOR_VERIFIED", "TRACE_REVIEW", "PENDING_HEAD_APPROVAL"]
NEEDS_ACTION = {"ACTION_PLANNED", "IN_PROGRESS", "EVIDENCE_SUBMITTED", "AUDITOR_VERIFIED",
                "REJECTED", "TRACE_REVIEW", "PENDING_HEAD_APPROVAL", "CLOSED"}
NEEDS_EVIDENCE = NEEDS_ACTION - {"ACTION_PLANNED", "IN_PROGRESS"}
NEEDS_VERIFY = {"AUDITOR_VERIFIED", "REJECTED", "TRACE_REVIEW", "PENDING_HEAD_APPROVAL", "CLOSED"}


# ------------------------------------------------------------------ helpers
def _hm(rng: random.Random, d: datetime) -> datetime:
    return d.replace(hour=rng.randint(8, 16), minute=rng.choice((0, 15, 30, 45)), second=0, microsecond=0)


def _rand_dt(rng: random.Random, lo: datetime, hi: datetime) -> datetime:
    d = lo + timedelta(seconds=rng.random() * (hi - lo).total_seconds())
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return _hm(rng, d)


def _clamp_dt(rng: random.Random, d: datetime) -> datetime:
    d = max(WINDOW_START + timedelta(days=1), min(d, WINDOW_END))
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return _hm(rng, d)


def _cluster_times(rng: random.Random, k: int) -> list[datetime]:
    span = rng.randint(60, 240)
    room = (WINDOW_END - WINDOW_START).days - span
    start = WINDOW_START + timedelta(days=rng.randint(0, room))
    offsets = [0] + sorted(rng.sample(range(1, span), k - 2)) + [span]
    times = []
    for off in offsets:
        d = start + timedelta(days=off)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        times.append(_hm(rng, d))
    times.sort()
    return times


def _deadline(raised: datetime, severity: str):
    return (raised + timedelta(days={"critical": 15, "major": 30, "minor": 45}[severity])).date()


def _lot(rng: random.Random, line: str, raised: datetime) -> str:
    return f"L{line[-1]}-{2200 + (raised - WINDOW_START).days // 3 + rng.randint(0, 2)}"


def _noise(rng: random.Random, text: str, prefix: bool = False) -> str:
    if rng.random() < 0.20:
        text = text.lower()
    if rng.random() < 0.20:
        for word, short in ABBREV.items():
            text = re.sub(rf"\b{word}\b", short, text, flags=re.IGNORECASE)
    if rng.random() < 0.25:
        words = text.split(" ")
        idxs = [i for i, w in enumerate(words) if len(w) > 4 and w.isalpha()]
        for i in rng.sample(idxs, k=min(len(idxs), rng.randint(1, 2))):
            w = words[i]
            j = rng.randrange(len(w) - 1)
            words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:]
        text = " ".join(words)
    if rng.random() < 0.30:
        text = text.rstrip(".")
    if prefix and rng.random() < 0.15:
        text = rng.choice(["During audit: ", "Observed: ", "Note - "]) + text
    return text


def _compose_text(rng, concept, rc, product, line, process, tpl_idx=None):
    bank = TEMPLATES[concept]
    title_t, desc_t = bank[tpl_idx if tpl_idx is not None else rng.randrange(len(bank))]
    f = {"part": PART_NAME[product], "feature": rng.choice(FEATURES), "line": line,
         "process_l": process.lower(), "audit": rng.choice(AUDITS)}
    desc = desc_t.format(**f)
    if rng.random() < 0.6:
        desc += " " + rng.choice(CAUSE_HINTS[rc])
    return _noise(rng, title_t.format(**f)), _noise(rng, desc, prefix=True)


def _outcome(rng, raised, target, mode, cap=None):
    """Return (status, closed_at). mode: auto | closed | open | pending."""
    age = (AS_OF - raised).days
    if mode == "auto":
        p = 0.92 if age > 120 else 0.8 if age > 60 else 0.55 if age > 30 else 0.2
        mode = "closed" if rng.random() < p else "open"
    if mode == "pending" and age < 8:
        mode = "open"
    if mode == "closed":
        lead = max(4, round(rng.gauss(24, 12)))
        if rng.random() < 0.25:  # late closure
            lead = max(lead, (target - raised.date()).days + rng.randint(3, 25))
        closed = raised + timedelta(days=lead, hours=rng.randint(1, 6))
        if cap is not None:
            closed = min(closed, cap)
        if raised + timedelta(days=4) <= closed <= AS_OF - timedelta(days=1):
            return "CLOSED", closed
        mode = "open"
    if mode == "pending":
        return rng.choice(PENDING_STATES), None
    if age < 5:
        return rng.choice(["OPEN", "ASSIGNED"]), None
    if age < 12:
        return rng.choice(["ASSIGNED", "ACTION_PLANNED", "IN_PROGRESS"]), None
    return rng.choice(OPEN_STATES), None


def _draft(rng, *, key, concept, rc, product, line, process, raised_at, cluster=False,
           mode="auto", p_symptom=0.55, cap=None, machine=None, lot=None, tpl_idx=None,
           title=None, description=None, fixed_id=None, fixed_outcome=None, kind=None,
           action_text=None, auditee=None):
    dept = tx.PROCESS_DEPARTMENT[process]
    if rc == "MAINTENANCE" and rng.random() < 0.3:
        dept = 7
    sev = rng.choices(("minor", "major", "critical"), weights=(15, 65, 20) if cluster else (40, 50, 10))[0]
    target = _deadline(raised_at, sev)
    if fixed_outcome is not None:
        status, closed_at = fixed_outcome
    else:
        status, closed_at = _outcome(rng, raised_at, target, mode, cap)
    if title is None:
        title, description = _compose_text(rng, concept, rc, product, line, process, tpl_idx)
    return {
        "key": key, "fixed_id": fixed_id, "concept": concept, "rc": rc, "product": product,
        "line": line, "process": process, "dept": dept,
        "audit_type": rng.choices(("product", "revalidation"), weights=(65, 35))[0],
        "severity": sev, "raised_at": raised_at, "target": target,
        "machine": machine or f"{PROCESS_PREFIX[process]}-{int(line[-1]):02d}",
        "lot": lot or _lot(rng, line, raised_at),
        "defect": CONCEPT_DEFECT[concept], "status": status, "closed_at": closed_at,
        "auditee": auditee or rng.choice(AUDITEES_BY_DEPT[dept]),
        "auditor": rng.choice(AUDITORS), "title": title, "description": description,
        "kind": kind or ("symptom" if rng.random() < p_symptom else "systemic"),
        "action_text": action_text,
    }


def _records(rng, nc, d, ids):
    action, evidence, verification = None, [], None
    if d["status"] not in NEEDS_ACTION:
        return action, evidence, verification
    symptom = d["kind"] == "symptom"
    created = nc.raised_at + timedelta(days=rng.randint(1, 2), hours=1)
    text = d["action_text"] or (rng.choice(SYMPTOM_ACTIONS) if symptom else SYSTEMIC_ACTIONS[d["rc"]])
    ids["action"] += 1
    action = ActionPlan(
        id=ids["action"], nc_id=nc.id, root_cause_category=d["rc"], corrective_action=text,
        preventive_action=None if symptom else "Add this check to the monthly audit checklist.",
        owner_id=d["auditee"], target_date=d["target"], created_at=created,
    )
    end = nc.closed_at or (AS_OF - timedelta(days=1))
    if d["status"] in NEEDS_EVIDENCE:
        ev_t = created + (end - created) * rng.uniform(0.35, 0.8)
        n_files = 1 if (symptom and rng.random() < 0.7) else rng.randint(2, 3)
        before_after = rng.random() < (0.3 if symptom else 0.75)
        for n in range(1, n_files + 1):
            ids["evidence"] += 1
            fname = f"{nc.id.lower()}-evidence-{n}.jpg"
            evidence.append(Evidence(
                id=ids["evidence"], nc_id=nc.id, file_url=f"https://example.invalid/ev/{fname}",
                file_name=fname, uploaded_by=d["auditee"],
                uploaded_at=ev_t + timedelta(minutes=5 * n),
                has_before_after=(n == 1 and before_after),
            ))
    if d["status"] in NEEDS_VERIFY:
        vt = ev_t + (end - ev_t) * rng.uniform(0.3, 0.8)
        accepted = d["status"] != "REJECTED"
        ids["verification"] += 1
        verification = Verification(
            id=ids["verification"], nc_id=nc.id, auditor_id=d["auditor"], accepted=accepted,
            comment=rng.choice(ACCEPT_COMMENTS if accepted else REJECT_COMMENTS), verified_at=vt,
        )
    return action, evidence, verification


def _cluster_facts(members: list[str], nc_by_id: dict[str, NC]):
    focus = max(members, key=lambda i: nc_by_id[i].raised_at)
    t = nc_by_id[focus].closed_at or AS_OF
    unresolved = sorted(
        m for m in members if m != focus and nc_by_id[m].raised_at < t
        and (nc_by_id[m].closed_at is None or nc_by_id[m].closed_at > t)
    )
    recurrences = []
    for r in sorted(members, key=lambda i: nc_by_id[i].raised_at):
        prior = [c for c in members if c != r and nc_by_id[c].closed_at is not None
                 and nc_by_id[c].closed_at < nc_by_id[r].raised_at]
        if prior:
            c = max(prior, key=lambda i: nc_by_id[i].closed_at)
            recurrences.append({
                "closed_nc": c, "recurred_nc": r,
                "closed_at": nc_by_id[c].closed_at.isoformat(),
                "raised_at": nc_by_id[r].raised_at.isoformat(),
                "days_after_closure": (nc_by_id[r].raised_at - nc_by_id[c].closed_at).days,
            })
    return focus, unresolved, recurrences


def _attrs(key, product, line, process, raised_at):
    return {"key": key, "product": product, "line": line, "process": process, "raised_at": raised_at}


# ------------------------------------------------------------------ generator
def generate(seed: int = SEED_DEFAULT) -> dict[str, Any]:
    rng = random.Random(seed)
    golden = build_golden()

    pairs_all = [(c, r) for c, rcs in CONCEPT_ROOT_CAUSES.items() for r in rcs]
    golden_pair = ("burr", "TOOL_LIFE")
    not_cluster = {golden_pair, ("coating", "MATERIAL"), ("dimension", "MEASUREMENT")}
    chosen = rng.sample([p for p in pairs_all if p not in not_cluster], N_CLUSTERS - 1)
    leftover = [p for p in pairs_all if p not in chosen and p != golden_pair]
    leftover_by = {c: [r for cc, r in leftover if cc == c] for c in CONCEPT_ROOT_CAUSES}

    split_ids = list(range(1, N_CLUSTERS))
    rng.shuffle(split_ids)
    test_ids = set(split_ids[:6])

    drafts: list[dict] = []

    # --- golden cluster C00: golden.py records + one supporting record (ADDITIONAL)
    support = _draft(
        rng, key="NC-0361", fixed_id="NC-0361", concept="burr", rc="TOOL_LIFE",
        product="Brake Drum", line="Line 4", process="Bore Machining",
        raised_at=datetime(2026, 4, 14, 10, 0), cluster=True,
        fixed_outcome=("CLOSED", datetime(2026, 5, 8, 15, 0)), machine="BM-04", lot="L4-2236",
        title="Rough lip on drum bore edge, Line 4",
        description="Rough lip felt on bore edge of brake drums at Line 4. Finishing insert worn beyond limit.",
        kind="symptom", action_text="Replaced finishing insert at Line 4 and reworked the affected lot.",
        auditee=202,
    )
    drafts.append(support)
    g_members = [_attrs("NC-0361", "Brake Drum", "Line 4", "Bore Machining", support["raised_at"])]
    for n in golden["ncs"]:
        if n.id in ("NC-0377", "NC-0390", "NC-0412"):
            g_members.append(_attrs(n.id, n.product, n.line, n.process, n.raised_at))
    cluster_defs = [{
        "id": "C00", "concept": "burr", "rc": "TOOL_LIFE", "home_product": "Brake Drum",
        "home_process": "Bore Machining", "members": g_members, "split": "golden",
        "keys": ["NC-0361", "NC-0377", "NC-0390", "NC-0412"],
    }]

    # --- planted clusters C01..C19
    for i, (concept, rc) in enumerate(chosen, start=1):
        cid = f"C{i:02d}"
        k = rng.randint(3, 6)
        home_product = rng.choice(tx.PRODUCTS)
        home_process = rng.choice(CONCEPT_PROCESSES[concept])
        times = _cluster_times(rng, k)
        modes = ["closed" if rng.random() < 0.6 else "open" for _ in range(k - 1)]
        if rng.random() < 0.8:
            modes[0] = "closed"                        # earlier closure -> later recurrence
        if rng.random() < 0.55:
            modes[rng.randrange(1, k - 1)] = "open"    # unresolved sibling
        modes.append(rng.choice(["pending", "pending", "open", "closed"]))
        cap = times[-1] - timedelta(days=2)
        order = rng.sample(range(5), 5)
        members: list[dict] = []
        for idx, t in enumerate(times):
            if members and rng.random() < 0.3:         # shared machine/lot lineage
                prev = rng.choice(members)
                product, line, process = prev["product"], prev["line"], prev["process"]
                machine, lot = prev["machine"], prev["lot"]
            else:
                product = home_product if rng.random() < 0.7 else rng.choice(tx.PRODUCTS)
                process = home_process if rng.random() < 0.55 else rng.choice(CONCEPT_PROCESSES[concept])
                line = rng.choice(tx.LINES)
                machine = lot = None
            members.append(_draft(
                rng, key=f"{cid}-{idx + 1}", concept=concept, rc=rc, product=product, line=line,
                process=process, raised_at=t, cluster=True, mode=modes[idx], p_symptom=0.65,
                cap=cap if idx == 0 else None, machine=machine, lot=lot, tpl_idx=order[idx % 5],
            ))
        drafts.extend(members)
        cluster_defs.append({
            "id": cid, "concept": concept, "rc": rc, "home_product": home_product,
            "home_process": home_process,
            "members": [_attrs(m["key"], m["product"], m["line"], m["process"], m["raised_at"]) for m in members],
            "split": "test" if i in test_ids else "dev", "keys": [m["key"] for m in members],
        })

    # --- decoys: look related, are NOT (different root cause or different defect)
    decoy_meta: dict[str, dict] = {}
    for n in range(1, N_DECOYS + 1):
        c = rng.choice(cluster_defs)
        key = f"D{n:03d}"
        kind = "text" if rng.random() < 0.5 else "structure"
        if kind == "text" and not leftover_by[c["concept"]]:
            kind = "structure"
        anchor = None
        if kind == "text":
            concept = c["concept"]
            rc = rng.choice(leftover_by[concept])
            product = rng.choice([p for p in tx.PRODUCTS if p != c["home_product"]])
            procs = [p for p in CONCEPT_PROCESSES[concept] if p != c["home_process"]] or CONCEPT_PROCESSES[concept]
            process = rng.choice(procs)
            line = rng.choice(tx.LINES)
            raised = _rand_dt(rng, WINDOW_START, WINDOW_END)
        else:
            anchor = rng.choice(c["members"])
            cands = [p for p in leftover if p[0] != c["concept"]
                     and anchor["process"] in CONCEPT_PROCESSES[p[0]]]
            cands = cands or [p for p in leftover if p[0] != c["concept"]]
            concept, rc = rng.choice(cands)
            product, line = anchor["product"], anchor["line"]
            process = anchor["process"] if anchor["process"] in CONCEPT_PROCESSES[concept] \
                else rng.choice(CONCEPT_PROCESSES[concept])
            raised = _clamp_dt(rng, anchor["raised_at"] + timedelta(days=rng.randint(-30, 30)))
        drafts.append(_draft(rng, key=key, concept=concept, rc=rc, product=product, line=line,
                             process=process, raised_at=raised, p_symptom=0.5))
        decoy_meta[key] = {"kind": kind, "resembles": c["id"], "anchor_key": anchor["key"] if anchor else None,
                           "cluster_split": c["split"]}

    # --- background singletons fill the rest
    n_bg = (N_TOTAL - N_GOLDEN_NCS) - len(drafts)
    assert n_bg > 0, "too many planted records for N_TOTAL"
    bg_keys = []
    for n in range(1, n_bg + 1):
        concept, rc = rng.choice(leftover)
        drafts.append(_draft(
            rng, key=f"B{n:03d}", concept=concept, rc=rc, product=rng.choice(tx.PRODUCTS),
            line=rng.choice(tx.LINES), process=rng.choice(CONCEPT_PROCESSES[concept]),
            raised_at=_rand_dt(rng, WINDOW_START, WINDOW_END), p_symptom=0.5,
        ))
        bg_keys.append(f"B{n:03d}")

    # --- chronological ids; the 6 reserved golden ids are skipped
    free = sorted((d for d in drafts if not d["fixed_id"]), key=lambda d: (d["raised_at"], d["key"]))
    pool = [i for i in range(1, N_TOTAL + 1) if i not in RESERVED_IDS]
    assert len(free) == len(pool)
    key_to_id = {d["key"]: d["fixed_id"] for d in drafts if d["fixed_id"]}
    for d, i in zip(free, pool):
        key_to_id[d["key"]] = f"NC-{i:04d}"

    # --- build contract objects
    ncs = list(golden["ncs"])
    action_plans = list(golden["action_plans"])
    evidence = list(golden["evidence"])
    verifications = list(golden["verifications"])
    action_scope = {k: list(v) for k, v in golden["scope_lines"].items()}
    action_kind = {"NC-0412": "symptom", "NC-0377": "symptom", "NC-0390": "symptom"}
    ids = {"action": 1000, "evidence": 1000, "verification": 1000}
    for d in sorted(drafts, key=lambda x: key_to_id[x["key"]]):
        nc = NC(
            id=key_to_id[d["key"]], audit_type=AuditType(d["audit_type"]), title=d["title"],
            description=d["description"], severity=Severity(d["severity"]), product=d["product"],
            process=d["process"], line=d["line"], department_id=d["dept"], machine=d["machine"],
            lot=d["lot"], defect_code=d["defect"], root_cause_category=d["rc"],
            status=NCStatus(d["status"]), auditee_id=d["auditee"], auditor_id=d["auditor"],
            raised_at=d["raised_at"], target_date=d["target"], closed_at=d["closed_at"],
        )
        ncs.append(nc)
        a, evs, v = _records(rng, nc, d, ids)
        if a:
            action_plans.append(a)
            action_scope[nc.id] = [d["line"]] if d["kind"] == "symptom" else list(tx.LINES)
            action_kind[nc.id] = d["kind"]
        evidence.extend(evs)
        if v:
            verifications.append(v)
    ncs.sort(key=lambda n: n.id)

    # --- ground truth (kept separate from the data the engine sees)
    nc_by_id = {n.id: n for n in ncs}
    gt_clusters, true_pairs, splits = [], [], {}
    for c in cluster_defs:
        mem = sorted(key_to_id.get(k, k) for k in c["keys"])
        focus, unresolved, rec = _cluster_facts(mem, nc_by_id)
        gt_clusters.append({
            "id": c["id"], "concept": c["concept"], "root_cause": c["rc"], "split": c["split"],
            "members": mem, "focus_nc": focus, "unresolved_at_focus": unresolved, "recurrences": rec,
        })
        true_pairs.extend([a, b] for a, b in itertools.combinations(mem, 2))
        for m in mem:
            splits[m] = c["split"]
    decoys_gt = {}
    for key in sorted(decoy_meta):
        meta = decoy_meta[key]
        nid = key_to_id[key]
        decoys_gt[nid] = {"kind": meta["kind"], "resembles": meta["resembles"],
                          "anchor_nc": key_to_id.get(meta["anchor_key"], meta["anchor_key"])}
        splits[nid] = meta["cluster_split"] if meta["cluster_split"] != "golden" else rng.choice(("dev", "test"))
    for gid in sorted(golden["expected"]["must_not_link"]):
        decoys_gt[gid] = {"kind": "golden", "resembles": "C00", "anchor_nc": "NC-0412"}
        splits[gid] = "golden"
    for key in bg_keys:
        splits[key_to_id[key]] = rng.choices(("dev", "test"), weights=(70, 30))[0]

    ground_truth = {
        "seed": seed, "as_of": AS_OF.isoformat(), "clusters": gt_clusters, "true_pairs": true_pairs,
        "decoys": decoys_gt, "background": sorted(key_to_id[k] for k in bg_keys),
        "splits": splits, "action_kind": action_kind,
        "counts": {"ncs": len(ncs), "clusters": len(gt_clusters), "decoys": len(decoys_gt),
                   "background": len(bg_keys)},
    }
    return {
        "seed": seed, "as_of": AS_OF, "ncs": ncs, "action_plans": action_plans,
        "evidence": evidence, "verifications": verifications, "action_scope": action_scope,
        "ground_truth": ground_truth,
    }


def write_outputs(data: dict[str, Any], out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    records: dict[str, Any] = {
        k: [m.model_dump(mode="json") for m in data[k]]
        for k in ("ncs", "action_plans", "evidence", "verifications")
    }
    records.update(action_scope=data["action_scope"], as_of=data["as_of"].isoformat(), seed=data["seed"])
    (out / "seed_data.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    (out / "ground_truth.json").write_text(json.dumps(data["ground_truth"], indent=2), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description="Generate synthetic TRACE seed data")
    p.add_argument("--seed", type=int, default=SEED_DEFAULT)
    p.add_argument("--out", default="seed/out")
    args = p.parse_args()
    data = generate(args.seed)
    write_outputs(data, args.out)
    print(f"wrote {len(data['ncs'])} NCs to {args.out} (seed={args.seed})")


if __name__ == "__main__":
    main()