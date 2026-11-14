import json
import sys
from collections import Counter
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from app.engine import taxonomy as t

from seed import generate as gen

# golden.py (Step 2) gives these two decoys no action/evidence records yet
GOLDEN_THIN = {"NC-0401", "NC-0408"}


@pytest.fixture(scope="module")
def data():
    return gen.generate(42)


def test_generator_tables_match_taxonomy():
    assert set(gen.CAUSE_HINTS) == set(t.ROOT_CAUSE_CATEGORIES)
    assert set(gen.SYSTEMIC_ACTIONS) == set(t.ROOT_CAUSE_CATEGORIES)
    assert set(gen.PROCESS_PREFIX) == set(t.PROCESSES)
    assert set(gen.CONCEPT_DEFECT.values()) <= set(t.DEFECT_CODES)
    assert set(gen.CONCEPT_DEFECT) == set(gen.TEMPLATES) == set(gen.CONCEPT_ROOT_CAUSES) == set(gen.CONCEPT_PROCESSES)
    for concept, rcs in gen.CONCEPT_ROOT_CAUSES.items():
        assert set(rcs) <= set(t.ROOT_CAUSE_CATEGORIES)
        assert set(gen.CONCEPT_PROCESSES[concept]) <= set(t.PROCESSES)
        assert len(gen.TEMPLATES[concept]) == 5


def test_counts_and_ids(data):
    ids = [n.id for n in data["ncs"]]
    assert len(ids) == 600
    assert set(ids) == {f"NC-{i:04d}" for i in range(1, 601)}


def test_deterministic(data):
    again = gen.generate(42)
    assert [n.model_dump(mode="json") for n in again["ncs"]] == [n.model_dump(mode="json") for n in data["ncs"]]
    assert again["ground_truth"] == data["ground_truth"]
    other = gen.generate(7)
    assert [n.title for n in other["ncs"]] != [n.title for n in data["ncs"]]


def test_canonical_fields(data):
    for n in data["ncs"]:
        errs = t.validate_fields(n.product, n.line, n.process, n.root_cause_category, n.defect_code)
        assert errs == [], (n.id, errs)
        assert n.department_id in t.DEPARTMENTS


def test_coverage(data):
    ncs = data["ncs"]
    assert {n.product for n in ncs} == set(t.PRODUCTS)
    assert {n.line for n in ncs} == set(t.LINES)
    assert {n.department_id for n in ncs} == set(t.DEPARTMENTS)
    assert len({(n.raised_at.year, n.raised_at.month) for n in ncs}) == 12


def test_records_reference_real_ncs_with_unique_ids(data):
    ids = {n.id for n in data["ncs"]}
    for key in ("action_plans", "evidence", "verifications"):
        recs = data[key]
        assert len({r.id for r in recs}) == len(recs)
        assert all(r.nc_id in ids for r in recs)


def test_status_and_records_are_consistent(data):
    actions = {a.nc_id for a in data["action_plans"]}
    evidence = {e.nc_id for e in data["evidence"]}
    verifs = {v.nc_id: v for v in data["verifications"]}
    for n in data["ncs"]:
        assert (n.status.value == "CLOSED") == (n.closed_at is not None), n.id
        if n.closed_at:
            assert n.closed_at > n.raised_at and n.closed_at <= data["as_of"]
        if n.id in GOLDEN_THIN:
            continue
        if n.status.value == "CLOSED":
            assert n.id in actions and n.id in evidence and verifs[n.id].accepted, n.id
        if n.status.value == "REJECTED":
            assert not verifs[n.id].accepted


def test_realistic_mix(data):
    ncs = data["ncs"]
    closed = [n for n in ncs if n.closed_at]
    assert 0.6 <= len(closed) / len(ncs) <= 0.92
    on_time = sum(1 for n in closed if n.closed_at.date() <= n.target_date)
    assert 0.3 <= on_time / len(closed) <= 0.9
    overdue = [n for n in ncs if not n.closed_at and n.target_date < data["as_of"].date()]
    assert len(overdue) >= 20


def test_both_action_kinds_exist(data):
    kinds = Counter(data["ground_truth"]["action_kind"].values())
    assert kinds["symptom"] > 100 and kinds["systemic"] > 100


def test_wording_is_varied(data):
    assert len({n.title for n in data["ncs"]}) > 250


def test_ground_truth_structure(data):
    gt = data["ground_truth"]
    ids = {n.id for n in data["ncs"]}
    assert len(gt["clusters"]) == 20
    assert Counter(c["split"] for c in gt["clusters"]) == {"golden": 1, "test": 6, "dev": 13}
    clustered = set()
    for c in gt["clusters"]:
        assert len(c["members"]) >= 3 and set(c["members"]) <= ids
        clustered |= set(c["members"])
    assert len(gt["true_pairs"]) == sum(comb(len(c["members"]), 2) for c in gt["clusters"])
    assert not (set(gt["decoys"]) & clustered)
    assert len(gt["decoys"]) == gen.N_DECOYS + 2
    assert set(gt["splits"]) == ids
    assert set(gt["splits"].values()) <= {"dev", "test", "golden"}
    c0 = next(c for c in gt["clusters"] if c["id"] == "C00")
    assert c0["members"] == ["NC-0361", "NC-0377", "NC-0390", "NC-0412"]
    assert c0["focus_nc"] == "NC-0412"
    assert c0["unresolved_at_focus"] == ["NC-0377"]
    assert any(r["closed_nc"] == "NC-0390" and r["recurred_nc"] == "NC-0412" for r in c0["recurrences"])


def test_escape_stories_exist(data):
    cl = data["ground_truth"]["clusters"]
    assert sum(1 for c in cl if c["recurrences"]) >= 12
    assert sum(1 for c in cl if c["unresolved_at_focus"]) >= 6


def test_write_outputs(data, tmp_path):
    gen.write_outputs(data, tmp_path)
    assert len(json.loads((tmp_path / "seed_data.json").read_text(encoding="utf-8"))["ncs"]) == 600
    assert "true_pairs" in json.loads((tmp_path / "ground_truth.json").read_text(encoding="utf-8"))