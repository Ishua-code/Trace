import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from app.engine.features import FeatureIndex
from app.engine.scoring import FrozenWeights, LinkScorer, load_weights, save_weights

from seed.golden import build_golden

W = FrozenWeights(
    bias=-3.0,
    weights={"same_product": 1.0, "same_root_cause": 2.0, "same_defect_code": 1.0,
             "time_proximity": 0.5, "glossary_overlap": 1.5},
    threshold=0.5,
    meta={},
)


@pytest.fixture
def scorer():
    return LinkScorer(FeatureIndex(build_golden()["ncs"]), W)


def others(links, nc_id):
    return [l.a if l.b == nc_id else l.b for l in links]


def test_score_pair_is_ordered_and_explained(scorer):
    link = scorer.score_pair("NC-0412", "NC-0377")
    assert (link.a, link.b) == ("NC-0377", "NC-0412")
    assert {s.name for s in link.signals} == set(W.weights)
    contributions = [s.contribution for s in link.signals]
    assert contributions == sorted(contributions, reverse=True)
    for s in link.signals:
        assert s.evidence
        assert s.contribution == pytest.approx(s.value * s.weight, abs=2e-3)
    logit = W.bias + sum(s.contribution for s in link.signals)
    assert link.score == pytest.approx(1 / (1 + math.exp(-logit)), abs=3e-3)


def test_related_golden_with_explicit_weights(scorer):
    links = scorer.related("NC-0412")
    assert others(links, "NC-0412") == ["NC-0377", "NC-0390"]      # best first
    assert not ({"NC-0401", "NC-0408"} & set(others(links, "NC-0412")))


def test_related_threshold_override_and_unknown(scorer):
    assert scorer.related("NC-0412", threshold=0.999) == []
    assert len(scorer.related("NC-0412", threshold=0.0)) == 4       # everyone but itself
    with pytest.raises(KeyError):
        scorer.related("NC-9999")


def test_deltas_change_effective_weights():
    idx = FeatureIndex(build_golden()["ncs"])
    base = LinkScorer(idx, W).score_pair("NC-0377", "NC-0412")
    adj = LinkScorer(idx, W, deltas={"same_root_cause": -2.0}).score_pair("NC-0377", "NC-0412")
    rc = next(s for s in adj.signals if s.name == "same_root_cause")
    assert rc.weight == pytest.approx(0.0) and adj.score < base.score


def test_all_links_are_symmetric(scorer):
    grouped = scorer.all_links()
    for nc_id, links in grouped.items():
        for l in links:
            assert l in grouped[l.b if l.a == nc_id else l.a]
    assert set(others(grouped["NC-0412"], "NC-0412")) == {"NC-0377", "NC-0390"}
    assert grouped["NC-0401"] == [] and grouped["NC-0408"] == []


def test_weights_roundtrip(tmp_path):
    p = tmp_path / "w.json"
    save_weights(W, p)
    back = load_weights(p)
    assert back.bias == W.bias and back.weights == W.weights and back.threshold == W.threshold


def test_missing_weights_file_has_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="eval.fit_weights"):
        load_weights(tmp_path / "nope.json")