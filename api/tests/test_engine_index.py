import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from app.engine.core import TraceEngineImpl
from app.engine.scoring import FrozenWeights
from app.engine.store import InMemoryStore

from seed.generate import generate
from seed.golden import build_golden

W = FrozenWeights(
    bias=-3.0,
    weights={"same_product": 1.0, "same_root_cause": 2.0, "same_defect_code": 1.0,
             "time_proximity": 0.5, "glossary_overlap": 1.5},
    threshold=0.5,
    meta={},
)


def _golden_engine():
    g = build_golden()
    store = InMemoryStore(g["ncs"], g["action_plans"], g["evidence"], g["verifications"],
                          g["scope_lines"])
    return TraceEngineImpl(store, weights=W), store


def test_index_nc_stores_links_visible_from_both_sides():
    engine, _ = _golden_engine()
    stored = engine.index_nc("NC-0412")
    assert len(stored) == 2 and all(l.id for l in stored)
    assert len(engine.find_related("NC-0412")) == 2
    assert any("NC-0412" in (l.a, l.b) for l in engine.find_related("NC-0377"))


def test_index_nc_is_idempotent_and_keeps_feedback():
    engine, store = _golden_engine()
    first = engine.index_nc("NC-0412")
    store.set_link_confirmed(first[0].id, True)
    again = engine.index_nc("NC-0412")
    assert [l.id for l in again] == [l.id for l in first]
    assert next(l for l in again if l.id == first[0].id).confirmed is True


def test_index_all_is_consistent():
    engine, store = _golden_engine()
    assert engine.index_all() == 3                      # 0377-0412, 0390-0412, 0377-0390
    assert len(store.get_links("NC-0412")) == 2
    assert len(store.get_links("NC-0377")) == 2
    assert store.get_links("NC-0401") == [] and store.get_links("NC-0408") == []


def test_index_nc_unknown_raises():
    engine, _ = _golden_engine()
    with pytest.raises(KeyError):
        engine.index_nc("NC-9999")


def test_index_nc_is_fast_on_full_seed():
    store = InMemoryStore.from_seed_data(generate(42))
    engine = TraceEngineImpl(store, weights=W)
    engine.refresh_index()
    for nc_id in ("NC-0412", "NC-0100", "NC-0500"):
        t0 = time.perf_counter()
        engine.index_nc(nc_id)
        assert time.perf_counter() - t0 < 0.5, nc_id     # warm; cold start is separate