"""One-off smoke test: python -m scripts.smoke_store   (run from the api/ folder)

Creates 2 throwaway NCs (ids ZZ-1, ZZ-2), exercises PostgresStore, then deletes everything it made.
"""
from datetime import datetime, timezone

from app.contracts import Link, Signal
from app.db import SessionLocal
from app import models as m
from app.pg_store import PostgresStore
from app.engine.store import NCStore
from app.engine.types import WeightUpdate


def main() -> None:
    db = SessionLocal()
    store = PostgresStore(db)
    assert isinstance(store, NCStore), "PostgresStore does not satisfy the NCStore protocol"
    now = datetime.now(timezone.utc)
    made_dept = False
    try:
        if db.get(m.Department, 999) is None:
            db.add(m.Department(id=999, name="ZZ test dept"))
            made_dept = True
        for nid in ("ZZ-1", "ZZ-2"):
            db.add(m.NC(
                id=nid, audit_type="product", title=nid, description="smoke", severity="minor",
                product="P", process="Pr", line="L1", department_id=999, status="OPEN", raised_at=now,
            ))
        db.commit()

        assert store.get_nc("ZZ-1").id == "ZZ-1"
        assert len(store.list_ncs()) >= 2

        sig = Signal(name="same_line", value=1.0, weight=0.5, contribution=0.5, evidence="L1")
        saved = store.save_links("ZZ-1", [Link(a="ZZ-1", b="ZZ-2", score=0.8, signals=[sig])])
        lid = saved[0].id
        assert lid is not None

        store.set_link_confirmed(lid, True)
        again = store.save_links("ZZ-1", [Link(a="ZZ-1", b="ZZ-2", score=0.9, signals=[sig])])
        assert again[0].id == lid and again[0].confirmed is True, "id/feedback must survive re-save"
        assert len(store.get_links("ZZ-2")) == 1

        store.save_weight_update(
            WeightUpdate(link_id=lid, confirmed=True, at=now, before={"same_line": 0.5}, after={"same_line": 0.55}),
            {"same_line": 0.05},
        )
        assert store.get_weight_deltas() == {"same_line": 0.05}
        assert len(store.list_weight_updates()) == 1

        try:
            store.save_links("ZZ-1", [Link(a="ZZ-2", b="ZZ-1", score=0.1, signals=[])])
            raise SystemExit("expected ValueError for a > b")
        except ValueError:
            pass

        print("PostgresStore smoke test: OK")
    finally:
        db.rollback()
        db.query(m.WeightUpdate).delete()
        db.query(m.WeightDelta).delete()
        db.query(m.Link).filter(m.Link.a.in_(["ZZ-1", "ZZ-2"])).delete(synchronize_session=False)
        db.query(m.NC).filter(m.NC.id.in_(["ZZ-1", "ZZ-2"])).delete(synchronize_session=False)
        if made_dept:
            db.query(m.Department).filter(m.Department.id == 999).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    main()
