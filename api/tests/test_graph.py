import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from app.contracts import NC, AuditType, Link, NCStatus, Severity, Signal
from app.engine.clock import FixedClock
from app.engine.core import TraceEngineImpl
from app.engine.graph import build_graph
from app.engine.scoring import FrozenWeights
from app.engine.store import InMemoryStore
from app.engine.taxonomy import DEPARTMENTS
from seed.golden import build_golden


def _at(text):
    return datetime.fromisoformat(text)


NOW = _at("2026-07-01T10:00:00")
W = FrozenWeights(
    bias=-3.0,
    weights={"same_product": 1.0, "same_root_cause": 2.0, "same_defect_code": 1.0,
             "time_proximity": 0.5, "glossary_overlap": 1.5},
    threshold=0.5,
    meta={},
)


def nc(i, status=NCStatus.CLOSED, product="Brake Drum", line="Line 1", process="Bore Machining",
       dept=2, raised=None):
    return NC(id=i, audit_type=AuditType.product, title=f"title {i}", description="d",
              severity=Severity.major, product=product, process=process, line=line,
              department_id=dept, status=status,
              raised_at=raised or _at("2026-06-21T10:00:00"))


def link(a, b, score, confirmed=None):
    a, b = sorted((a, b))
    sig = [Signal(name="same_product", value=1.0, weight=1.0, contribution=1.0, evidence="x")]
    return Link(a=a, b=b, score=score, signals=sig, confirmed=confirmed)


def make_store(ncs, links):
    store = InMemoryStore(ncs)
    saved = {}
    for lk in links:
        saved.setdefault(lk.a, []).append(lk)
    # save_links replaces everything touching an NC, so write each pair once via its smaller id
    for nc_id in sorted(saved):
        keep = [x for x in store.get_links(nc_id) if nc_id in (x.a, x.b)]
        store.save_links(nc_id, keep + saved[nc_id])
    for lk in links:
        if lk.confirmed is not None:
            stored = next(x for x in store.get_links(lk.a) if (x.a, x.b) == (lk.a, lk.b))
            store.set_link_confirmed(stored.id, lk.confirmed)
    return store


def chain_store(extra=()):
    ncs = [
        nc("A", NCStatus.AUDITOR_VERIFIED, line="Line 2"),
        nc("B", NCStatus.CLOSED, product="Wheel Hub", line="Line 3", process="Heat Treatment",
           dept=3),
        nc("C", NCStatus.IN_PROGRESS, line="Line 4"),
        nc("D", NCStatus.OPEN, line="Line 5", process="Final Inspection", dept=6),
        nc("E", NCStatus.OPEN),
    ]
    return make_store(ncs, [link("A", "B", 0.9), link("B", "C", 0.8), link("C", "D", 0.7), *extra])


def paths_by_target(graph):
    return {p.target: p for p in graph.paths}


def test_hop_cap_two_reaches_c_through_closed_b_but_not_d():
    g = build_graph(chain_store(), "A", NOW, max_hops=2)
    assert {n.id for n in g.nodes} == {"A", "B", "C"}
    paths = paths_by_target(g)
    assert set(paths) == {"C"}  # B is closed so it is not a target; D is 3 hops away
    assert paths["C"].source == "A"
    assert paths["C"].hops == ["A", "B", "C"] and paths["C"].scores == [0.9, 0.8]


def test_hop_cap_three_adds_d_and_e_is_never_reached():
    g = build_graph(chain_store(), "A", NOW, max_hops=3)
    assert set(paths_by_target(g)) == {"C", "D"}
    assert paths_by_target(g)["D"].hops == ["A", "B", "C", "D"]
    assert "E" not in {n.id for n in g.nodes}


def test_paths_are_ranked_strongest_first():
    g = build_graph(chain_store(), "A", NOW, max_hops=3)
    assert [p.target for p in g.paths] == ["C", "D"]  # 0.72 then 0.504


def test_strongest_path_beats_the_shorter_weaker_one():
    store = chain_store([link("A", "C", 0.5)])  # direct 0.5 vs via B 0.9 * 0.8 = 0.72
    p = paths_by_target(build_graph(store, "A", NOW))["C"]
    assert p.hops == ["A", "B", "C"]


def test_equal_strength_prefers_fewer_hops():
    ncs = [nc("A"), nc("B"), nc("C", NCStatus.OPEN)]
    store = make_store(ncs, [link("A", "B", 0.5), link("B", "C", 0.5), link("A", "C", 0.25)])
    assert paths_by_target(build_graph(store, "A", NOW))["C"].hops == ["A", "C"]


def test_rejected_link_is_drawn_but_not_walked():
    ncs = [nc("A"), nc("B"), nc("C", NCStatus.OPEN)]
    store = make_store(ncs, [link("A", "B", 0.9), link("A", "C", 0.6),
                             link("B", "C", 0.95, confirmed=False)])
    g = build_graph(store, "A", NOW)
    assert paths_by_target(g)["C"].hops == ["A", "C"]  # never through the rejected B-C link
    edge = next(e for e in g.edges if (e.a, e.b) == ("B", "C"))
    assert edge.confirmed is False


def test_nc_reachable_only_through_a_rejected_link_is_left_out():
    ncs = [nc("A"), nc("B"), nc("C", NCStatus.OPEN)]
    store = make_store(ncs, [link("A", "B", 0.9), link("B", "C", 0.95, confirmed=False)])
    g = build_graph(store, "A", NOW)
    assert {n.id for n in g.nodes} == {"A", "B"} and g.paths == []


def test_a_rejected_shortcut_does_not_hide_the_real_path():
    ncs = [nc("A"), nc("B"), nc("C", NCStatus.OPEN)]
    store = make_store(ncs, [link("A", "B", 0.9), link("B", "C", 0.8),
                             link("A", "C", 0.99, confirmed=False)])
    assert paths_by_target(build_graph(store, "A", NOW))["C"].hops == ["A", "B", "C"]


def test_confirmed_and_unreviewed_links_are_both_used():
    ncs = [nc("A"), nc("B", NCStatus.OPEN), nc("C", NCStatus.OPEN)]
    store = make_store(ncs, [link("A", "B", 0.9, confirmed=True), link("A", "C", 0.6)])
    assert set(paths_by_target(build_graph(store, "A", NOW))) == {"B", "C"}


def test_unresolved_means_everything_but_closed():
    ncs = [nc("A")] + [nc(f"R{i}", s) for i, s in enumerate(
        [NCStatus.REJECTED, NCStatus.TRACE_REVIEW, NCStatus.CLOSED])]
    store = make_store(ncs, [link("A", n.id, 0.8) for n in ncs[1:]])
    targets = set(paths_by_target(build_graph(store, "A", NOW)))
    assert targets == {"R0", "R1"}


def test_focus_with_no_links_is_a_single_node():
    g = build_graph(chain_store(), "E", NOW)
    assert [n.id for n in g.nodes] == ["E"] and g.edges == [] and g.paths == []
    assert g.clusters == {} and g.footprint["products"] == ["Brake Drum"]


def test_footprint_covers_focus_and_unresolved_targets_only():
    g = build_graph(chain_store(), "A", NOW, max_hops=3)  # A, C, D affected; B is closed
    assert g.footprint == {
        "products": ["Brake Drum"],
        "lines": ["Line 2", "Line 4", "Line 5"],
        "processes": ["Bore Machining", "Final Inspection"],
        "departments": sorted({DEPARTMENTS[2], DEPARTMENTS[6]}),
    }


def test_linked_groups_and_node_cluster_ids():
    ncs = [nc("A"), nc("B"), nc("C", NCStatus.OPEN)]
    g = build_graph(make_store(ncs, [link("A", "B", 0.9), link("B", "C", 0.8)]), "A", NOW)
    assert g.clusters == {"G1": ["A", "B", "C"]}
    assert {n.cluster_id for n in g.nodes} == {"G1"}


def test_age_days_uses_the_engine_clock():
    g = build_graph(chain_store(), "A", NOW)
    assert {n.id: n.age_days for n in g.nodes}["A"] == 10
    late = _at("2026-06-01T00:00:00")  # before raised_at never goes negative
    assert build_graph(chain_store(), "A", late).nodes[0].age_days == 0


def test_unknown_nc_and_bad_hop_cap():
    with pytest.raises(KeyError):
        build_graph(chain_store(), "NOPE", NOW)
    for bad in (0, 5):
        with pytest.raises(ValueError):
            build_graph(chain_store(), "A", NOW, max_hops=bad)


def test_deterministic_and_does_not_change_the_store():
    store = chain_store()
    before = [(x.id, x.a, x.b, x.score, x.confirmed) for n in "ABCDE" for x in store.get_links(n)]
    first = build_graph(store, "A", NOW, max_hops=3)
    second = build_graph(store, "A", NOW, max_hops=3)
    assert first == second
    after = [(x.id, x.a, x.b, x.score, x.confirmed) for n in "ABCDE" for x in store.get_links(n)]
    assert before == after


def test_edges_are_listed_once_with_link_ids():
    g = build_graph(chain_store(), "A", NOW, max_hops=3)
    keys = [(e.a, e.b) for e in g.edges]
    assert keys == sorted(set(keys)) and all(e.a < e.b and e.link_id for e in g.edges)


# ---------------------------------------------------------------- golden scenario
def _golden_engine():
    g = build_golden()
    store = InMemoryStore(g["ncs"], g["action_plans"], g["evidence"], g["verifications"],
                          g["scope_lines"])
    return TraceEngineImpl(store, clock=FixedClock(_at("2026-07-01T00:00:00")), weights=W)


def test_golden_graph_from_the_engine():
    engine = _golden_engine()
    engine.index_all()
    g = engine.get_graph("NC-0412")
    ids = {n.id for n in g.nodes}
    assert {"NC-0377", "NC-0390"} <= ids
    assert not ({"NC-0401", "NC-0408"} & ids)  # decoys are never pulled in
    on_paths = {h for p in g.paths for h in p.hops}
    assert not ({"NC-0401", "NC-0408"} & on_paths)
    targets = paths_by_target(g)
    assert set(targets) == {"NC-0377"}  # NC-0390 is already closed
    assert targets["NC-0377"].hops == ["NC-0412", "NC-0377"]
    assert "Brake Drum" in g.footprint["products"] and "Line 4" in g.footprint["lines"]


def test_engine_get_graph_unknown_nc():
    with pytest.raises(KeyError):
        _golden_engine().get_graph("NC-9999")