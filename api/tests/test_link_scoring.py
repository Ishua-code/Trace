import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from app.engine.core import TraceEngineImpl
from app.engine.features import ALL_FEATURES
from app.engine.scoring import WEIGHTS_PATH, load_weights
from app.engine.store import InMemoryStore

from seed.generate import generate


@pytest.fixture(scope="module")
def golden_links():
    engine = TraceEngineImpl(InMemoryStore.from_seed_data(generate(42)))
    links = engine.index_nc("NC-0412")
    return links, {l.a if l.b == "NC-0412" else l.b for l in links}


def test_frozen_weights_exist_and_are_dev_only():
    assert WEIGHTS_PATH.exists(), "run: python -m eval.fit_weights"
    w = load_weights()
    assert set(w.weights) == set(ALL_FEATURES) and 0 < w.threshold < 1
    assert w.meta["trained_on_split"] == "dev"
    assert {"test", "golden"} <= set(w.meta["excluded_splits"])


def test_golden_links_nc_0377(golden_links):
    assert "NC-0377" in golden_links[1]


def test_golden_links_nc_0390(golden_links):
    assert "NC-0390" in golden_links[1]      # weakest link, see notes


def test_golden_links_nc_0361(golden_links):
    assert "NC-0361" in golden_links[1]


def test_golden_decoys_do_not_link(golden_links):
    assert not ({"NC-0401", "NC-0408"} & golden_links[1])


def test_every_link_is_explained(golden_links):
    for l in golden_links[0]:
        assert l.signals and all(s.evidence for s in l.signals)