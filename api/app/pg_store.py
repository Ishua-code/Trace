"""NCStore on Postgres. Mirrors engine/store.py::InMemoryStore behaviour.

The engine imports only the NCStore Protocol; this is the production implementation.
Every write commits (one short transaction per call).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.contracts import NC, ActionPlan, Evidence, Link, Verification
from app.engine.store import pair_key
from app.engine.types import WeightUpdate


def _to(cls, row):
    """ORM row -> contract object. Extra columns are ignored by pydantic."""
    return cls.model_validate({c.name: getattr(row, c.name) for c in row.__table__.columns})


class PostgresStore:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------------------------------------------------------------- reads
    def get_nc(self, nc_id: str) -> Optional[NC]:
        row = self.db.get(m.NC, nc_id)
        return _to(NC, row) if row else None

    def list_ncs(self) -> list[NC]:
        rows = self.db.scalars(select(m.NC).order_by(m.NC.id)).all()
        return [_to(NC, r) for r in rows]

    def get_actions(self, nc_id: str) -> list[ActionPlan]:
        rows = self.db.scalars(
            select(m.ActionPlan).where(m.ActionPlan.nc_id == nc_id).order_by(m.ActionPlan.id)
        ).all()
        return [_to(ActionPlan, r) for r in rows]

    def get_action_scope_lines(self, nc_id: str) -> Optional[list[str]]:
        """Union of applies_to_lines over the NC's action plans; None if no plan states a scope."""
        rows = self.db.scalars(select(m.ActionPlan).where(m.ActionPlan.nc_id == nc_id)).all()
        scoped = [r.applies_to_lines for r in rows if r.applies_to_lines is not None]
        if not scoped:
            return None
        lines: list[str] = []
        for group in scoped:
            for line in group:
                if line not in lines:
                    lines.append(line)
        return lines

    def get_evidence(self, nc_id: str) -> list[Evidence]:
        rows = self.db.scalars(
            select(m.Evidence).where(m.Evidence.nc_id == nc_id).order_by(m.Evidence.id)
        ).all()
        return [_to(Evidence, r) for r in rows]

    def get_verifications(self, nc_id: str) -> list[Verification]:
        rows = self.db.scalars(
            select(m.Verification).where(m.Verification.nc_id == nc_id).order_by(m.Verification.id)
        ).all()
        return [_to(Verification, r) for r in rows]

    # ---------------------------------------------------------------- links
    @staticmethod
    def _link(row: m.Link) -> Link:
        return Link.model_validate(
            {"id": row.id, "a": row.a, "b": row.b, "score": row.score,
             "signals": row.signals, "confirmed": row.confirmed}
        )

    def get_links(self, nc_id: str) -> list[Link]:
        rows = self.db.scalars(
            select(m.Link).where((m.Link.a == nc_id) | (m.Link.b == nc_id))
        ).all()
        rows = sorted(rows, key=lambda r: (-r.score, r.a, r.b))
        return [self._link(r) for r in rows]

    def save_links(self, nc_id: str, links: list[Link]) -> list[Link]:
        """Replace every stored link touching nc_id. A pair that already existed keeps its
        id and its auditor feedback. All input is validated before anything changes."""
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
                if self.db.get(m.NC, x) is None:
                    raise KeyError(x)
            seen.add(key)
            prepared.append((key, link))

        old_rows = self.db.scalars(
            select(m.Link).where((m.Link.a == nc_id) | (m.Link.b == nc_id))
        ).all()
        old = {(r.a, r.b): r for r in old_rows}

        # drop only links that are no longer wanted (keeps ids + weight_updates of kept pairs)
        for key, row in old.items():
            if key not in seen:
                self.db.delete(row)

        saved_rows: list[m.Link] = []
        for key, link in prepared:
            signals = [s.model_dump(mode="json") for s in link.signals]
            row = old.get(key)
            if row is not None:
                row.score = link.score
                row.signals = signals
                if row.confirmed is None:
                    row.confirmed = link.confirmed
            else:
                row = m.Link(a=key[0], b=key[1], score=link.score,
                             signals=signals, confirmed=link.confirmed)
                self.db.add(row)
            saved_rows.append(row)
        self.db.commit()
        return [self._link(r) for r in saved_rows]

    def get_link(self, link_id: int) -> Optional[Link]:
        row = self.db.get(m.Link, link_id)
        return self._link(row) if row else None

    def set_link_confirmed(self, link_id: int, confirmed: bool) -> None:
        row = self.db.get(m.Link, link_id)
        if row is None:
            raise KeyError(link_id)
        row.confirmed = confirmed
        self.db.commit()

    # ---------------------------------------------------------------- learning loop
    def get_weight_deltas(self) -> dict[str, float]:
        return {r.name: r.delta for r in self.db.scalars(select(m.WeightDelta)).all()}

    def save_weight_update(self, update: WeightUpdate, new_deltas: dict[str, float]) -> None:
        self.db.add(m.WeightUpdate(
            link_id=update.link_id, confirmed=update.confirmed, at=update.at,
            before=update.before, after=update.after,
        ))
        existing = {r.name: r for r in self.db.scalars(select(m.WeightDelta)).all()}
        for name, delta in new_deltas.items():
            if name in existing:
                existing[name].delta = delta
            else:
                self.db.add(m.WeightDelta(name=name, delta=delta))
        for name, row in existing.items():
            if name not in new_deltas:
                self.db.delete(row)
        self.db.commit()

    def list_weight_updates(self) -> list[WeightUpdate]:
        rows = self.db.scalars(select(m.WeightUpdate).order_by(m.WeightUpdate.id)).all()
        return [
            WeightUpdate(link_id=r.link_id, confirmed=r.confirmed, at=r.at,
                         before=r.before, after=r.after)
            for r in rows
        ]
