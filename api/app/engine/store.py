"""Data-access interface for the engine, plus an in-memory implementation.

The engine imports only this module's Protocol, never a database. Ishwarya
implements NCStore on Postgres; seed, tests and eval use InMemoryStore.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Protocol, runtime_checkable

from app.contracts import ActionPlan, Evidence, Link, NC, NCStatus, Verification
from app.engine.types import WeightUpdate


def pair_key(a: str, b: str) -> tuple[str, str]:
    """Canonical (smaller, larger) order so (A,B) and (B,A) are one link."""
    if a == b:
        raise ValueError("a link needs two different NCs")
    return (a, b) if a < b else (b, a)


def is_unresolved(nc: NC) -> bool:
    """Unresolved means any status except CLOSED (REOPENED and REJECTED count)."""
    return nc.status != NCStatus.CLOSED


@runtime_checkable
class NCStore(Protocol):
    def get_nc(self, nc_id: str) -> Optional[NC]: ...
    def list_ncs(self) -> list[NC]: ...
    def get_actions(self, nc_id: str) -> list[ActionPlan]: ...
    def get_action_scope_lines(self, nc_id: str) -> Optional[list[str]]: ...
    def get_evidence(self, nc_id: str) -> list[Evidence]: ...
    def get_verifications(self, nc_id: str) -> list[Verification]: ...
    def get_links(self, nc_id: str) -> list[Link]: ...
    def save_links(self, nc_id: str, links: list[Link]) -> list[Link]: ...
    def get_link(self, link_id: int) -> Optional[Link]: ...
    def set_link_confirmed(self, link_id: int, confirmed: bool) -> None: ...
    def get_weight_deltas(self) -> dict[str, float]: ...
    def save_weight_update(self, update: WeightUpdate, new_deltas: dict[str, float]) -> None: ...
    def list_weight_updates(self) -> list[WeightUpdate]: ...


class InMemoryStore:
    """Reference implementation. Returned objects are copies; callers cannot mutate state."""

    def __init__(
        self,
        ncs,
        action_plans=(),
        evidence=(),
        verifications=(),
        action_scope: Optional[dict[str, list[str]]] = None,
    ) -> None:
        self._ncs: dict[str, NC] = {n.id: n for n in ncs}
        self._actions = self._group(action_plans)
        self._evidence = self._group(evidence)
        self._verifs = self._group(verifications)
        self._scope: dict[str, list[str]] = {k: list(v) for k, v in (action_scope or {}).items()}
        self._links: dict[tuple[str, str], Link] = {}
        self._key_by_id: dict[int, tuple[str, str]] = {}
        self._next_link_id = 1
        self._deltas: dict[str, float] = {}
        self._updates: list[WeightUpdate] = []

    @staticmethod
    def _group(records) -> dict[str, list]:
        out: dict[str, list] = {}
        for r in records:
            out.setdefault(r.nc_id, []).append(r)
        return out

    @classmethod
    def from_seed_data(cls, data: dict[str, Any]) -> "InMemoryStore":
        return cls(
            data["ncs"], data["action_plans"], data["evidence"],
            data["verifications"], data.get("action_scope"),
        )

    # ---- reads
    def get_nc(self, nc_id: str) -> Optional[NC]:
        return self._ncs.get(nc_id)

    def list_ncs(self) -> list[NC]:
        return [self._ncs[k] for k in sorted(self._ncs)]

    def get_actions(self, nc_id: str) -> list[ActionPlan]:
        return list(self._actions.get(nc_id, []))

    def get_action_scope_lines(self, nc_id: str) -> Optional[list[str]]:
        lines = self._scope.get(nc_id)
        return list(lines) if lines is not None else None

    def get_evidence(self, nc_id: str) -> list[Evidence]:
        return list(self._evidence.get(nc_id, []))

    def get_verifications(self, nc_id: str) -> list[Verification]:
        return list(self._verifs.get(nc_id, []))

    # ---- links
    def get_links(self, nc_id: str) -> list[Link]:
        found = [l for k, l in self._links.items() if nc_id in k]
        found.sort(key=lambda l: (-l.score, l.a, l.b))
        return [l.model_copy(deep=True) for l in found]

    def save_links(self, nc_id: str, links: list[Link]) -> list[Link]:
        """Replace every stored link that touches nc_id with `links`.

        A pair that already existed keeps its id and any auditor feedback.
        All input is validated before anything changes.
        """
        prepared: list[tuple[tuple[str, str], Link]] = []
        seen: set[tuple[str, str]] = set()
        for link in links:
            key = pair_key(link.a, link.b)
            if (link.a, link.b) != key:
                raise ValueError(f"link must be stored with a < b: {link.a}, {link.b}")
            if nc_id not in key:
                raise ValueError(f"link {key} does not involve {nc_id}")
            if key in seen:
                raise ValueError(f"duplicate link {key}")
            for x in key:
                if x not in self._ncs:
                    raise KeyError(x)
            seen.add(key)
            prepared.append((key, link))

        old = {k: l for k, l in self._links.items() if nc_id in k}
        for k, l in old.items():
            del self._links[k]
            self._key_by_id.pop(l.id, None)

        saved: list[Link] = []
        for key, link in prepared:
            prev = old.get(key)
            if prev is not None:
                lid = prev.id
                confirmed = prev.confirmed if prev.confirmed is not None else link.confirmed
            else:
                lid = self._next_link_id
                self._next_link_id += 1
                confirmed = link.confirmed
            stored = link.model_copy(update={"id": lid, "confirmed": confirmed}, deep=True)
            self._links[key] = stored
            self._key_by_id[lid] = key
            saved.append(stored.model_copy(deep=True))
        return saved

    def get_link(self, link_id: int) -> Optional[Link]:
        key = self._key_by_id.get(link_id)
        return self._links[key].model_copy(deep=True) if key else None

    def set_link_confirmed(self, link_id: int, confirmed: bool) -> None:
        key = self._key_by_id.get(link_id)
        if key is None:
            raise KeyError(link_id)
        self._links[key] = self._links[key].model_copy(update={"confirmed": confirmed})

    # ---- learning loop state
    def get_weight_deltas(self) -> dict[str, float]:
        return dict(self._deltas)

    def save_weight_update(self, update: WeightUpdate, new_deltas: dict[str, float]) -> None:
        self._updates.append(update)
        self._deltas = dict(new_deltas)

    def list_weight_updates(self) -> list[WeightUpdate]:
        return list(self._updates)

    # ---- time travel (used by eval replay)
    def snapshot_as_of(self, when: datetime) -> "InMemoryStore":
        """A fresh store showing only what existed at `when`, with no stored links.

        Guarantees OPEN vs CLOSED is right as of `when`. Other workflow states are
        left as they are now (an approximation, noted in docs/engine.md).
        """
        ncs = []
        for n in self._ncs.values():
            if n.raised_at > when:
                continue
            if n.closed_at is not None and n.closed_at > when:
                n = n.model_copy(update={"closed_at": None, "status": NCStatus.IN_PROGRESS})
            ncs.append(n)
        keep = {n.id for n in ncs}

        def pick(groups: dict[str, list], attr: str) -> list:
            return [r for k, rs in groups.items() if k in keep for r in rs if getattr(r, attr) <= when]

        return InMemoryStore(
            ncs,
            pick(self._actions, "created_at"),
            pick(self._evidence, "uploaded_at"),
            pick(self._verifs, "verified_at"),
            {k: v for k, v in self._scope.items() if k in keep},
        )