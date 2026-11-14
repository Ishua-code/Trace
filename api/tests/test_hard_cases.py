import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from app.engine import glossary as g
from app.engine import taxonomy as t

from seed.hard_cases import content_words, load_hard_cases


@pytest.fixture(scope="module")
def cases():
    return load_hard_cases()


def _concepts(nc):
    return g.concepts_in(f"{nc.title} {nc.description}")


def test_shape(cases):
    assert len(cases) == 40
    assert Counter(c["label"] for c in cases) == {True: 28, False: 12}
    assert Counter(c["needs"] for c in cases) == {"glossary": 11, "structure": 14, "both": 3, "decoy": 12}
    ids = [n.id for c in cases for n in (c["a"], c["b"])]
    assert len(ids) == len(set(ids)) == 80


def test_canonical_fields(cases):
    for c in cases:
        for n in (c["a"], c["b"]):
            errs = t.validate_fields(n.product, n.line, n.process, n.root_cause_category, n.defect_code)
            assert errs == [], (n.id, errs)


def test_no_shared_keywords(cases):
    for c in cases:
        shared = content_words(c["a"].title, c["a"].description) & content_words(c["b"].title, c["b"].description)
        assert not shared, (c["id"], shared)


def test_each_group_tests_the_signal_it_claims(cases):
    for c in cases:
        a, b = c["a"], c["b"]
        shared_concepts = _concepts(a) & _concepts(b)
        same_site = a.machine == b.machine or a.lot == b.lot
        if c["needs"] == "glossary":
            assert shared_concepts, c["id"]
            assert a.root_cause_category is None and b.root_cause_category is None
            assert a.product == b.product and a.defect_code == b.defect_code
        elif c["needs"] == "structure":
            assert not shared_concepts, c["id"]          # glossary cannot help here
            assert same_site and a.root_cause_category == b.root_cause_category, c["id"]
        elif c["needs"] == "both":
            assert shared_concepts and same_site, c["id"]
        else:  # decoy
            assert not shared_concepts, c["id"]
            assert a.product == b.product and a.line == b.line and same_site, c["id"]
            assert a.root_cause_category != b.root_cause_category, c["id"]
            assert a.defect_code != b.defect_code or a.root_cause_category != b.root_cause_category