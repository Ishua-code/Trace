import copy
import dataclasses
import hashlib
import inspect
import itertools
import json
import math
import pickle
import sys
from collections import Counter
from pathlib import Path
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pytest
from app.engine.features import (
    FeatureIndex,
    FrozenIdf,
    fit_idf,
    tokenize,
)

from eval.cv import build_dev_pairs
from eval.frozen_idf import (
    dev_ids_digest,
    dev_ncs,
    fit_dev_idf,
    main,
    write_dev_idf,
)
from seed.generate import generate

UNSEEN = "qzvxk"


@pytest.fixture(scope="module")
def data():
    return generate(42)


@pytest.fixture(scope="module")
def dev(data):
    return dev_ncs(data)


@pytest.fixture(scope="module")
def frozen(data):
    return fit_dev_idf(data)


def _text(nc):
    return f"{nc.title} {nc.description}"


def reference_idf(ncs):
    """The ORIGINAL FeatureIndex formula, written out independently of the implementation."""
    ncs = list(ncs)
    docs = {nc.id: set(tokenize(_text(nc))) for nc in ncs}  # document frequency counts an id once
    df = Counter()
    for tokens in docs.values():
        df.update(tokens)
    n = len(ncs)
    return n, {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}, math.log(1 + n) + 1.0


def reference_cosine(ncs, a_id, b_id):
    _, idf, default = reference_idf(ncs)
    by_id = {nc.id: nc for nc in ncs}

    def vec(nc):
        counts = Counter(tokenize(_text(nc)))
        raw = {t: (1.0 + math.log(c)) * idf.get(t, default) for t, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in raw.values())) or 1.0
        return {t: v / norm for t, v in raw.items()}

    va, vb = vec(by_id[a_id]), vec(by_id[b_id])
    return min(1.0, sum(w * vb[t] for t, w in va.items() if t in vb))


def sample_pairs(ncs, k=25):
    return list(itertools.combinations([nc.id for nc in ncs[:k]], 2))


def known_token(idf):
    return next(t for t in sorted(idf.idf) if tokenize(t) == [t])


# ---------------------------------------------------------------- default behaviour unchanged
def test_signature_adds_only_a_keyword_only_idf():
    params = inspect.signature(FeatureIndex).parameters
    assert list(params) == ["ncs", "idf"]
    assert params["idf"].kind is inspect.Parameter.KEYWORD_ONLY and params["idf"].default is None


def test_default_idf_is_the_original_formula_exactly(data):
    ncs = data["ncs"]
    n, idf, default = reference_idf(ncs)
    built = FeatureIndex(ncs).idf
    assert built.n_docs == n and built.default_idf == default
    assert dict(built.idf) == idf  # exact float equality, not approx
    assert built == fit_idf(ncs)


def test_duplicate_ids_behave_as_before(dev):
    ncs = [*dev[:20], dev[0]]  # same id twice: n counts the list, df counts the id once
    n, idf, default = reference_idf(ncs)
    built = fit_idf(ncs)
    assert built.n_docs == n == 21 and built.default_idf == default and dict(built.idf) == idf
    assert FeatureIndex(ncs).idf == built


def test_default_pair_features_match_an_independent_tfidf(dev):
    sub = dev[:60]
    idx = FeatureIndex(sub)
    for a, b in sample_pairs(sub, 15):
        assert idx.pair_features(a, b)["tfidf_cosine"] == pytest.approx(
            reference_cosine(sub, a, b), abs=1e-12
        )


def test_idf_only_changes_the_tfidf_feature(data, dev, frozen):
    default = FeatureIndex(data["ncs"])  # IDF fitted on all 600 NCs, as before
    dev_only = FeatureIndex(data["ncs"], idf=frozen)
    assert default.idf != dev_only.idf
    differs = False
    for a, b in sample_pairs(dev):
        fa, fb = default.pair_features(a, b), dev_only.pair_features(a, b)
        for name in fa:
            if name == "tfidf_cosine":
                differs = differs or abs(fa[name] - fb[name]) > 1e-9
            else:
                assert fa[name] == fb[name], name
    assert differs  # the test is not vacuous: the two IDFs really give different cosines


# ---------------------------------------------------------------- fit time == runtime
def test_runtime_index_applies_exactly_the_fitted_transformation(data, dev, frozen):
    fit_time = FeatureIndex(dev)  # what the fitter builds from DEV NCs alone
    runtime = FeatureIndex(data["ncs"], idf=frozen)  # a runtime index that also holds TEST/GOLDEN
    assert fit_time.idf == frozen and runtime.idf is frozen
    for a, b in sample_pairs(dev, 40):
        assert fit_time.pair_features(a, b) == runtime.pair_features(a, b)  # bit-identical
        for name in ("tfidf_cosine",):
            assert fit_time.evidence(a, b, name, 0.3) == runtime.evidence(a, b, name, 0.3)


def test_saved_and_reloaded_statistics_score_identically(data, dev, frozen, tmp_path):
    path = tmp_path / "idf.json"
    frozen.save(path)
    loaded = FrozenIdf.load(path)
    a, b = FeatureIndex(dev, idf=frozen), FeatureIndex(dev, idf=loaded)
    for x, y in sample_pairs(dev, 40):
        assert a.pair_features(x, y) == b.pair_features(x, y)


# ---------------------------------------------------------------- upsert and unseen tokens
def test_unseen_tokens_get_the_stored_default_idf(dev, frozen):
    known = known_token(frozen)
    assert UNSEEN not in frozen.idf and frozen.weight(UNSEEN) == frozen.default_idf
    update = {"id": "NC-TEST-UNSEEN", "title": f"{known} {UNSEEN}", "description": ""}
    nc = dev[0].model_copy(update=update)
    vec = FeatureIndex([nc], idf=frozen)._docs[nc.id].vec
    assert set(vec) == {known, UNSEEN}
    # equal term frequency, so the ratio of the two weights is the ratio of their IDFs
    expected = frozen.default_idf / frozen.idf[known]
    assert vec[UNSEEN] / vec[known] == pytest.approx(expected, rel=1e-12)


def test_upsert_never_changes_the_frozen_statistics(dev, frozen):
    idx = FeatureIndex(dev, idf=frozen)
    before_digest, before_items = frozen.digest, dict(frozen.idf)
    before_vecs = {i: idx._docs[i].vec for i in idx.ids[:10]}
    known = known_token(frozen)
    novel = dev[0].model_copy(update={"id": "NC-TEST-NEW", "title": f"{known} {UNSEEN} {UNSEEN}"})
    idx.upsert(novel)  # a new NC full of unseen tokens
    refresh = {"description": f"{UNSEEN} {UNSEEN} rewritten"}
    idx.upsert(dev[1].model_copy(update=refresh))  # refresh an existing NC
    assert idx.idf is frozen and frozen.digest == before_digest and dict(frozen.idf) == before_items
    assert UNSEEN not in frozen.idf  # the new vocabulary was NOT absorbed
    assert "NC-TEST-NEW" in idx
    for i, vec in before_vecs.items():
        if i != dev[1].id:
            assert idx._docs[i].vec == vec  # untouched NCs keep their vectors


def test_upsert_scores_new_nc_with_the_frozen_idf(dev, frozen):
    idx = FeatureIndex(dev, idf=frozen)
    twin = dev[0].model_copy(update={"id": "NC-TEST-TWIN"})
    idx.upsert(twin)
    assert idx.pair_features(dev[0].id, twin.id)["tfidf_cosine"] == pytest.approx(1.0)
    assert FeatureIndex([*dev, twin], idf=frozen).pair_features(dev[0].id, dev[2].id) == (
        idx.pair_features(dev[0].id, dev[2].id)
    )


# ---------------------------------------------------------------- immutability and hashing
def test_frozen_idf_is_immutable(frozen):
    for attr, value in (("n_docs", 1), ("default_idf", 1.0), ("items", ())):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(frozen, attr, value)
    with pytest.raises(TypeError):
        frozen.idf["x"] = 1.0
    assert isinstance(frozen.items, tuple)


def test_internal_lookup_is_a_genuinely_read_only_mapping(dev):
    idf = fit_idf(dev[:30])
    digest, snapshot = idf.digest, dict(idf.idf)
    lookup = idf._lookup
    assert isinstance(lookup, MappingProxyType) and idf.idf is lookup
    key = min(snapshot)
    with pytest.raises(TypeError):
        lookup["zzinjected"] = 1.0
    with pytest.raises(TypeError):
        lookup[key] = 0.0
    with pytest.raises(TypeError):
        del lookup[key]
    assert not any(hasattr(lookup, name) for name in ("update", "pop", "clear", "setdefault"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        idf._lookup = {}
    assert dict(idf.idf) == snapshot and idf.digest == digest and idf.weight(key) == snapshot[key]
    assert idf == fit_idf(dev[:30])  # digest still matches a fresh fit


def test_frozen_idf_copies_and_pickles_by_value(dev):
    idf = fit_idf(dev[:30])
    for clone in (copy.copy(idf), copy.deepcopy(idf), pickle.loads(pickle.dumps(idf))):
        assert clone == idf and clone.items == idf.items and clone.digest == idf.digest
        with pytest.raises(TypeError):
            clone.idf["zzinjected"] = 1.0
    idx = copy.deepcopy(FeatureIndex(dev[:10], idf=idf))  # an index holding it copies too
    assert idx.idf == idf


def test_frozen_idf_copies_its_input():
    source = {"alpha": 1.5, "beta": 2.5}
    idf = FrozenIdf.from_mapping(3, source, 3.0)
    source["alpha"] = 99.0
    source["gamma"] = 1.0
    assert dict(idf.idf) == {"alpha": 1.5, "beta": 2.5}


def test_frozen_idf_is_hashable_and_compares_by_content(data, dev):
    a, b = fit_idf(dev), fit_idf(list(reversed(dev)))
    assert a == b and hash(a) == hash(b) and a.digest == b.digest  # input order is irrelevant
    assert {a: "x"}[b] == "x" and len({a, b}) == 1
    other = fit_idf(dev[:-1])
    assert a != other and a.digest != other.digest and len({a, other}) == 2
    assert a != "not an idf"


def test_frozen_idf_validates_its_values():
    with pytest.raises(ValueError):
        FrozenIdf.from_mapping(1, {"a": float("nan")}, 2.0)
    with pytest.raises(ValueError):
        FrozenIdf.from_mapping(1, {"a": 1.0}, float("inf"))
    with pytest.raises(ValueError):
        FrozenIdf.from_mapping(-1, {"a": 1.0}, 2.0)
    with pytest.raises(ValueError):
        FrozenIdf.from_mapping(True, {"a": 1.0}, 2.0)
    with pytest.raises(ValueError):
        FrozenIdf(1, 2.0, (("a", 1.0), ("a", 2.0)))


# ---------------------------------------------------------------- DEV-only isolation
def test_dev_set_is_exactly_the_420_dev_ncs(data, dev, frozen):
    splits = data["ground_truth"]["splits"]
    expected = {i for i, s in splits.items() if s == "dev"}
    assert len(dev) == 420 == frozen.n_docs
    assert {nc.id for nc in dev} == expected == set(build_dev_pairs(data).ids)
    assert not ({nc.id for nc in dev} & {i for i, s in splits.items() if s != "dev"})
    blob = "\n".join(sorted(expected)).encode("utf-8")
    assert dev_ids_digest(dev) == hashlib.sha256(blob).hexdigest()


def test_vocabulary_is_exactly_the_dev_vocabulary(dev, frozen):
    assert set(frozen.idf) == {t for nc in dev for t in tokenize(_text(nc))}
    n, idf, default = reference_idf(dev)
    assert frozen.n_docs == n and frozen.default_idf == default and dict(frozen.idf) == idf


def test_changing_test_and_golden_text_changes_nothing(data, frozen):
    splits = data["ground_truth"]["splits"]
    novel = ("zzalpha", "zzbeta", "zzgamma", "zzdelta")
    rewrite = {"title": "zzalpha zzbeta brake drum", "description": "zzgamma zzdelta " * 6}
    changed = [
        nc.model_copy(update=rewrite) if splits[nc.id] != "dev" else nc for nc in data["ncs"]
    ]
    again = fit_dev_idf({**data, "ncs": changed})
    assert again == frozen and again.digest == frozen.digest and again.items == frozen.items
    assert not (set(novel) & set(again.idf))


def test_removing_test_and_golden_ncs_changes_nothing(data, frozen):
    splits = data["ground_truth"]["splits"]
    only_dev = [nc for nc in data["ncs"] if splits[nc.id] == "dev"]
    assert fit_dev_idf({**data, "ncs": only_dev}).digest == frozen.digest


def test_changing_dev_text_does_change_the_statistics(data, dev, frozen):
    splits = data["ground_truth"]["splits"]
    first = dev[0].id
    edited = [
        nc.model_copy(update={"title": "zzalpha brake drum"}) if nc.id == first else nc
        for nc in data["ncs"]
    ]
    assert splits[first] == "dev"
    assert fit_dev_idf({**data, "ncs": edited}).digest != frozen.digest  # the digest is sensitive


@pytest.mark.parametrize("kind", ["test", "golden"])
def test_non_dev_input_is_rejected_explicitly(data, dev, kind):
    splits = data["ground_truth"]["splits"]
    outsider = next(nc for nc in data["ncs"] if splits[nc.id] == kind)
    with pytest.raises(ValueError, match="non-dev") as err:
        fit_dev_idf(data, ncs=[*dev, outsider])
    message = str(err.value)
    assert kind in message and outsider.id not in message  # names the split, not the id
    with pytest.raises(ValueError, match="non-dev"):
        fit_dev_idf(data, ncs=[outsider])


def test_all_ncs_and_unlabelled_ncs_are_rejected(data, dev):
    with pytest.raises(ValueError, match="non-dev"):
        fit_dev_idf(data, ncs=data["ncs"])
    stranger = dev[0].model_copy(update={"id": "NC-NOT-IN-SPLITS"})
    with pytest.raises(ValueError, match="non-dev"):
        fit_dev_idf(data, ncs=[*dev, stranger])
    with pytest.raises(ValueError, match="no split label"):
        dev_ncs({**data, "ncs": [*data["ncs"], stranger]})


def test_empty_and_duplicate_inputs_are_rejected(data, dev):
    with pytest.raises(ValueError, match="no NCs"):
        fit_dev_idf(data, ncs=[])
    with pytest.raises(ValueError, match="duplicate"):
        fit_dev_idf(data, ncs=[*dev, dev[0]])


def test_explicit_dev_list_matches_the_default(data, dev, frozen):
    assert fit_dev_idf(data, ncs=dev) == frozen


# ---------------------------------------------------------------- JSON round trip and tampering
def test_json_round_trip_is_exact_and_deterministic(frozen, tmp_path):
    path = tmp_path / "idf.json"
    frozen.save(path)
    loaded = FrozenIdf.load(path)
    assert loaded == frozen and loaded.digest == frozen.digest
    assert loaded.items == frozen.items and loaded.n_docs == frozen.n_docs  # floats survive exactly
    assert loaded.default_idf == frozen.default_idf
    again = tmp_path / "again.json"
    loaded.save(again)
    assert again.read_bytes() == path.read_bytes()
    assert json.loads(path.read_text())["sha256"] == frozen.digest


def small_idf(dev):
    return fit_idf(dev[:20])


def _drop_token(p):
    p["idf"].pop(min(p["idf"]))


def _add_token(p):
    p["idf"]["zzinjected"] = 1.0


def _nudge_value(p):
    key = min(p["idf"])
    p["idf"][key] += 1e-6


TAMPERS = {
    "value": _nudge_value,
    "dropped token": _drop_token,
    "added token": _add_token,
    "n_docs": lambda p: p.__setitem__("n_docs", p["n_docs"] + 1),
    "default_idf": lambda p: p.__setitem__("default_idf", p["default_idf"] + 1e-6),
    "wrong digest": lambda p: p.__setitem__("sha256", "0" * 64),
    "missing digest": lambda p: p.pop("sha256"),
    "version": lambda p: p.__setitem__("version", 2),
    "scheme": lambda p: p.__setitem__("scheme", "something else"),
    "non-finite": lambda p: p.__setitem__("default_idf", float("nan")),
    "n_docs type": lambda p: p.__setitem__("n_docs", "20"),
    "value type": lambda p: p["idf"].__setitem__(min(p["idf"]), None),
}


@pytest.mark.parametrize("name", list(TAMPERS))
def test_tampered_files_are_rejected(dev, tmp_path, name):  # content problems -> ValueError
    idf = small_idf(dev)
    payload = json.loads(idf.to_json())
    TAMPERS[name](payload)
    path = tmp_path / "idf.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        FrozenIdf.load(path)


def test_wrong_json_shapes_raise_type_error(dev, tmp_path):
    payload = json.loads(small_idf(dev).to_json())
    payload["idf"] = [1, 2]  # 'idf' must be an object
    path = tmp_path / "idf.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TypeError, match="idf"):
        FrozenIdf.load(path)
    for text in ("[]", "null", '"text"', "5"):  # the document itself must be an object
        with pytest.raises(TypeError, match="JSON object"):
            FrozenIdf.from_json(text)


def test_digest_mismatch_message_and_untouched_file_still_loads(dev, tmp_path):
    idf = small_idf(dev)
    payload = json.loads(idf.to_json())
    _nudge_value(payload)
    with pytest.raises(ValueError, match="digest mismatch"):
        FrozenIdf.from_json(json.dumps(payload))
    assert FrozenIdf.from_json(idf.to_json()) == idf


def test_garbage_files_are_rejected():
    for text in ("", "not json", '{"version": 1}'):
        with pytest.raises(ValueError):
            FrozenIdf.from_json(text)


# ---------------------------------------------------------------- writing (explicit path only)
def test_write_dev_idf_writes_only_where_asked(data, frozen, tmp_path):
    target = tmp_path / "somewhere" / "idf.json"
    target.parent.mkdir()
    written = write_dev_idf(data, target)
    assert written == frozen and FrozenIdf.load(target) == frozen
    assert [p.name for p in tmp_path.rglob("*") if p.is_file()] == ["idf.json"]


def test_cli_requires_an_explicit_output_path(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main([])
    out = tmp_path / "idf.json"
    main(["--out", str(out)])
    assert FrozenIdf.load(out).n_docs == 420
    assert "dev ids sha256" in capsys.readouterr().out