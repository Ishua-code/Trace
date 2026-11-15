import math
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from app.engine.features import (
    ALL_FEATURES,
    STRUCTURAL_FEATURES,
    TEXT_FEATURES,
    FeatureIndex,
    tokenize,
)

from seed.golden import build_golden

UNRELATED = {"title": "Quartz spindle vibrates", "description": "Coolant pump humming loudly"}


@pytest.fixture(scope="module")
def ncs():
    return {n.id: n for n in build_golden()["ncs"]}


@pytest.fixture
def index(ncs):
    return FeatureIndex(ncs.values())


def _copy(nc, new_id, **kw):
    return nc.model_copy(update={"id": new_id, **kw})


def test_feature_names():
    assert len(ALL_FEATURES) == 12 == len(set(ALL_FEATURES))
    assert ALL_FEATURES == STRUCTURAL_FEATURES + TEXT_FEATURES


def test_tokenize():
    assert tokenize("Burr on Brake-Drums, bore!") == ["burr", "brake", "drum", "bore"]


def test_structural_flags_on_golden_pair(index):
    f = index.pair_features("NC-0377", "NC-0412")
    assert f["same_product"] == 1 and f["same_process"] == 1 and f["same_department"] == 1
    assert f["same_root_cause"] == 1 and f["same_defect_code"] == 1
    assert f["same_line"] == 0 and f["same_machine"] == 0 and f["same_lot"] == 0
    assert 0 < f["time_proximity"] < 0.5


def test_missing_values_never_match(ncs):
    none = {"root_cause_category": None, "defect_code": None, "machine": None,
            "lot": None, "line": None}
    idx = FeatureIndex([_copy(ncs["NC-0412"], "NC-9001", **none),
                        _copy(ncs["NC-0412"], "NC-9002", **none)])
    f = idx.pair_features("NC-9001", "NC-9002")
    for name in ("same_root_cause", "same_defect_code", "same_machine", "same_lot", "same_line"):
        assert f[name] == 0, name


def test_time_proximity(ncs):
    base = ncs["NC-0412"]
    idx = FeatureIndex([
        _copy(base, "NC-9001"),
        _copy(base, "NC-9002"),
        _copy(base, "NC-9003", raised_at=base.raised_at + timedelta(days=90)),
        _copy(base, "NC-9004", raised_at=base.raised_at + timedelta(days=300)),
    ])
    assert idx.pair_features("NC-9001", "NC-9002")["time_proximity"] == pytest.approx(1.0)
    assert idx.pair_features("NC-9001", "NC-9003")["time_proximity"] == pytest.approx(math.exp(-1))
    assert (idx.pair_features("NC-9001", "NC-9004")["time_proximity"]
            < idx.pair_features("NC-9001", "NC-9003")["time_proximity"])


def test_text_features_identical_and_unrelated(ncs):
    base = ncs["NC-0412"]
    idx = FeatureIndex([_copy(base, "NC-9001"), _copy(base, "NC-9002"),
                        _copy(base, "NC-9003", **UNRELATED)])
    same = idx.pair_features("NC-9001", "NC-9002")
    assert same["tfidf_cosine"] == pytest.approx(1.0)
    assert same["char_similarity"] == pytest.approx(1.0)
    assert same["glossary_overlap"] == pytest.approx(1.0)
    diff = idx.pair_features("NC-9001", "NC-9003")
    assert diff["tfidf_cosine"] == 0.0 and diff["glossary_overlap"] == 0.0
    assert diff["char_similarity"] < 0.5


def test_glossary_overlap_is_partial_for_golden_pair(index):
    assert 0 < index.pair_features("NC-0377", "NC-0412")["glossary_overlap"] < 1


def test_features_are_symmetric_and_bounded(index):
    ids = index.ids
    for a in ids:
        for b in ids:
            if a == b:
                continue
            f1, f2 = index.pair_features(a, b), index.pair_features(b, a)
            assert f1 == f2
            assert all(0.0 <= v <= 1.000001 for v in f1.values())


def test_unknown_nc_raises(index):
    with pytest.raises(KeyError):
        index.pair_features("NC-0412", "NC-9999")


def test_upsert_changes_text_features(ncs):
    idx = FeatureIndex(ncs.values())
    before = idx.pair_features("NC-0377", "NC-0412")["tfidf_cosine"]
    idx.upsert(_copy(ncs["NC-0412"], "NC-0412", **UNRELATED))
    after = idx.pair_features("NC-0377", "NC-0412")["tfidf_cosine"]
    assert before > 0 and after == 0.0


def test_evidence_strings(index):
    ev = lambda n, v=1.0: index.evidence("NC-0377", "NC-0412", n, v)
    assert "Brake Drum" in ev("same_product")
    assert "TOOL_LIFE" in ev("same_root_cause")
    assert "days apart" in ev("time_proximity")
    assert "burr" in ev("glossary_overlap")
    assert ev("tfidf_cosine", 0.3).startswith("Shared wording")
    assert "%" in ev("char_similarity", 0.41)


def test_feature_matrix(index):
    np = pytest.importorskip("numpy")
    m = index.feature_matrix([("NC-0377", "NC-0412"), ("NC-0390", "NC-0412")], ALL_FEATURES)
    assert m.shape == (2, 12)
    assert np.all(m >= 0) and np.all(m <= 1.000001)