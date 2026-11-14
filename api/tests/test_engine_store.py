import inspect
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from seed.golden import build_golden

from app.contracts import Link, Signal, TraceEngine
from app.engine.clock import FixedClock, SystemClock
from app.engine.core import TraceEngineImpl
from app.engine.store import InMemoryStore, NCStore, is_unresolved, pair_key
from app.engine.types import WeightUpdate


def _link(a, b, score=0.8):
    a, b = pair_key(a, b)
    sig = Signal(name="same_product", value=1.0, weight=0.5, contribution=0.5, evidence="Both Brake Drum")
    return Link(a=a, b=b, score=score, signals=[sig])


@pytest.fixture
def store():
    g = build_golden()
    return InMemoryStore(g["ncs"], g["action_plans"], g["evidence"], g["verifications"], g["scope_lines"])


def test_store_satisfies_protocol(store):
    assert isinstance(store, NCStore)


def test_pair_key():
    assert pair_key("NC-0412", "NC-0377") == ("NC-0377", "NC-0412")
    with pytest.raises(ValueError):
        pair_key("NC-0001", "NC-0001")


def test_unresolved_definition(store):
    assert is_unresolved(store.get_nc("NC-0377"))
    assert not is_unresolved(store.get_nc("NC-0390"))


def test_reads(store):
    assert store.get_nc("NC-9999") is None
    ids = [n.id for n in store.list_ncs()]
    assert ids == sorted(ids) and len(ids) == 5
    assert len(store.get_actions("NC-0412")) == 1
    assert len(store.get_evidence("NC-0412")) == 1
    assert len(store.get_verifications("NC-0412")) == 1
    assert store.get_action_scope_lines("NC-0412") == ["Line 2"]
    assert store.get_action_scope_lines("NC-0401") is None


def test_save_links_assigns_ids_and_sorts(store):
    saved = store.save_links("NC-0412", [_link("NC-0412", "NC-0390", 0.6), _link("NC-0412", "NC-0377", 0.9)])
    assert sorted(l.id for l in saved) == [1, 2]
    got = store.get_links("NC-0412")
    assert [l.score for l in got] == [0.9, 0.6]
    assert [l.b for l in store.get_links("NC-0377")] == ["NC-0412"]


def test_save_links_validation_leaves_store_untouched(store):
    store.save_links("NC-0412", [_link("NC-0412", "NC-0377")])
    bad_order = Link(a="NC-0412", b="NC-0377", score=0.5, signals=[])
    with pytest.raises(ValueError):
        store.save_links("NC-0412", [bad_order])
    with pytest.raises(ValueError):
        store.save_links("NC-0412", [_link("NC-0377", "NC-0390")])
    with pytest.raises(ValueError):
        store.save_links("NC-0412", [_link("NC-0412", "NC-0390"), _link("NC-0412", "NC-0390")])
    with pytest.raises(KeyError):
        store.save_links("NC-0412", [_link("NC-0412", "NC-7777")])
    assert len(store.get_links("NC-0412")) == 1


def test_resave_keeps_id_and_feedback(store):
    first = store.save_links("NC-0412", [_link("NC-0412", "NC-0377", 0.7)])[0]
    store.set_link_confirmed(first.id, True)
    again = store.save_links("NC-0412", [_link("NC-0412", "NC-0377", 0.95)])[0]
    assert again.id == first.id and again.confirmed is True and again.score == 0.95


def test_resave_drops_stale_links(store):
    two = store.save_links("NC-0412", [_link("NC-0412", "NC-0377"), _link("NC-0412", "NC-0390")])
    store.save_links("NC-0412", [_link("NC-0412", "NC-0377")])
    stale = next(l for l in two if l.b == "NC-0412" and l.a == "NC-0390")
    assert store.get_link(stale.id) is None
    assert len(store.get_links("NC-0412")) == 1


def test_confirm_unknown_link(store):
    with pytest.raises(KeyError):
        store.set_link_confirmed(99, True)


def test_returned_links_are_copies(store):
    store.save_links("NC-0412", [_link("NC-0412", "NC-0377")])
    got = store.get_links("NC-0412")
    got[0].score = 0.0
    got.clear()
    assert store.get_links("NC-0412")[0].score == 0.8


def test_weight_updates(store):
    upd = WeightUpdate(link_id=1, confirmed=True, at=datetime(2026, 11, 1), before={"w": 0.5}, after={"w": 0.52})
    store.save_weight_update(upd, {"w": 0.02})
    deltas = store.get_weight_deltas()
    assert deltas == {"w": 0.02}
    deltas["w"] = 9.0
    assert store.get_weight_deltas() == {"w": 0.02}
    assert len(store.list_weight_updates()) == 1


def test_snapshot_as_of_hides_the_future(store):
    snap = store.snapshot_as_of(datetime(2026, 7, 15))
    assert {n.id for n in snap.list_ncs()} == {"NC-0377", "NC-0390"}
    nc390 = snap.get_nc("NC-0390")
    assert nc390.closed_at is None and is_unresolved(nc390)       # closed later, still open then
    assert snap.get_evidence("NC-0390") == []                     # uploaded in August
    assert len(snap.get_actions("NC-0390")) == 1                  # created in June
    assert store.get_nc("NC-0390").closed_at is not None          # original untouched


def test_snapshot_after_closure_shows_closed(store):
    snap = store.snapshot_as_of(datetime(2026, 8, 20))
    assert not is_unresolved(snap.get_nc("NC-0390"))


def test_from_seed_data():
    from seed.generate import generate

    s = InMemoryStore.from_seed_data(generate(42))
    assert len(s.list_ncs()) == 600
    assert s.get_nc("NC-0361") is not None
    assert s.get_action_scope_lines("NC-0361") == ["Line 4"]


def test_clock():
    c = FixedClock(datetime(2026, 11, 12, 9, 0))
    assert c.now() == datetime(2026, 11, 12, 9, 0)
    c.advance(days=1)
    assert c.now() == datetime(2026, 11, 13, 9, 0)
    assert isinstance(SystemClock().now(), datetime)


def test_engine_signatures_match_contract():
    for name in ("find_related", "simulate_closure", "plan_risk", "record_feedback"):
        want = list(inspect.signature(getattr(TraceEngine, name)).parameters)
        got = list(inspect.signature(getattr(TraceEngineImpl, name)).parameters)
        assert got == want, name


def test_find_related_reads_stored_links(store):
    engine = TraceEngineImpl(store)
    store.save_links("NC-0412", [_link("NC-0412", "NC-0377"), _link("NC-0412", "NC-0390")])
    assert len(engine.find_related("NC-0412")) == 2
    with pytest.raises(KeyError):
        engine.find_related("NC-9999")