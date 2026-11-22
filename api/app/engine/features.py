"""Pair features for link scoring (structural + textual signals).

Pure Python. numpy is imported lazily and only by feature_matrix (offline fitting/eval).
Every feature is in [0, 1] and symmetric: f(a, b) == f(b, a).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from app.contracts import NC
from app.engine import glossary, taxonomy

STRUCTURAL_FEATURES = (
    "same_product", "same_line", "same_process", "same_department",
    "same_root_cause", "same_defect_code", "same_machine", "same_lot",
    "time_proximity",
)
TEXT_FEATURES = ("tfidf_cosine", "char_similarity", "glossary_overlap")
ALL_FEATURES = STRUCTURAL_FEATURES + TEXT_FEATURES

TIME_SCALE_DAYS = 90.0

_STOP = frozenset(
    [
        "the", "and", "with", "for", "was", "were", "are", "been", "has", "had", "not", "but",
        "from", "that", "this", "into", "onto", "over", "under", "after", "before", "during",
        "when", "while", "than", "then", "there", "their", "its", "can", "may", "one", "two", "all",
        "any", "per", "off", "out", "also",
    ]
)
_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    out: list[str] = []
    for w in _TOKEN.findall(text.lower()):
        if len(w) < 3 or w in _STOP:
            continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


def trigrams(text: str) -> frozenset[str]:
    norm = " ".join(_TOKEN.findall(text.lower()))
    padded = f"  {norm} "
    return frozenset(padded[i:i + 3] for i in range(len(padded) - 2))


def _dot(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return min(1.0, sum(w * b[t] for t, w in a.items() if t in b))


def _dice(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return 2.0 * len(a & b) / (len(a) + len(b))


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _same(x: object, y: object) -> float:
    return float(x is not None and x == y)


@dataclass(frozen=True)
class Doc:
    nc: NC
    vec: dict[str, float]
    grams: frozenset[str]
    concepts: frozenset[str]


IDF_FORMAT_VERSION = 1
IDF_SCHEME = "smooth-idf: ln((1+n)/(1+df))+1; unseen token: ln(1+n)+1"


def _idf_digest(n_docs: int, default_idf: float, items: tuple[tuple[str, float], ...]) -> str:
    """SHA-256 over a canonical serialisation (sorted tokens, shortest round-trip floats)."""
    body = {
        "version": IDF_FORMAT_VERSION,
        "scheme": IDF_SCHEME,
        "n_docs": n_docs,
        "default_idf": default_idf,
        "idf": [[t, v] for t, v in items],
    }
    blob = json.dumps(body, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True, eq=False, repr=False)
class FrozenIdf:
    """Immutable, hashable IDF statistics: n_docs, one weight per token, a default weight.

    Fitting and serving share this object, so both apply exactly the same transformation.
    Equality and hash follow the SHA-256 digest of the content. Build one with fit_idf or
    FrozenIdf.from_mapping, or load a saved file with FrozenIdf.load (which verifies the digest).
    """

    n_docs: int
    default_idf: float
    items: tuple[tuple[str, float], ...]
    # derived in __post_init__; the lookup is a read-only mapping, its dict is not reachable
    _lookup: Mapping[str, float] = field(init=False, repr=False, compare=False)
    _digest: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if isinstance(self.n_docs, bool) or not isinstance(self.n_docs, int) or self.n_docs < 0:
            raise ValueError("n_docs must be a non-negative integer")
        default = float(self.default_idf)
        items = tuple(sorted((str(t), float(v)) for t, v in self.items))
        if not math.isfinite(default) or not all(math.isfinite(v) for _, v in items):
            raise ValueError("IDF values must be finite")
        if len({t for t, _ in items}) != len(items):
            raise ValueError("duplicate token in IDF items")
        object.__setattr__(self, "default_idf", default)
        object.__setattr__(self, "items", items)
        object.__setattr__(self, "_lookup", MappingProxyType(dict(items)))
        object.__setattr__(self, "_digest", _idf_digest(self.n_docs, default, items))

    @classmethod
    def from_mapping(cls, n_docs: int, idf: Mapping[str, float], default_idf: float) -> FrozenIdf:
        return cls(n_docs, default_idf, tuple(idf.items()))

    @property
    def idf(self) -> Mapping[str, float]:
        """Read-only view of token -> IDF weight."""
        return self._lookup

    @property
    def digest(self) -> str:
        return self._digest

    def weight(self, token: str) -> float:
        """IDF of a token; a token never seen when the statistics were fitted gets default_idf."""
        return self._lookup.get(token, self.default_idf)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FrozenIdf) and self.digest == other.digest

    def __hash__(self) -> int:
        return hash(self.digest)

    def __repr__(self) -> str:
        return (
            f"FrozenIdf(n_docs={self.n_docs}, tokens={len(self.items)}, "
            f"sha256={self.digest[:12]})"
        )

    def __reduce__(self):
        """Copy and pickle by rebuilding (a read-only mapping cannot be pickled itself)."""
        return (FrozenIdf, (self.n_docs, self.default_idf, self.items))

    # ---- persistence
    def to_json(self) -> str:
        payload = {
            "version": IDF_FORMAT_VERSION,
            "scheme": IDF_SCHEME,
            "n_docs": self.n_docs,
            "default_idf": self.default_idf,
            "idf": dict(self.items),
            "sha256": self.digest,
        }
        return json.dumps(payload, indent=1, sort_keys=True, allow_nan=False) + "\n"

    def save(self, path: Path | str) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def from_json(cls, text: str) -> FrozenIdf:
        """Parse and verify the file content.

        Raises TypeError when the JSON has the wrong shape (not an object, or `idf` not an
        object) and ValueError for invalid JSON or malformed, altered or incomplete content.
        """
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"IDF file is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise TypeError("IDF file must hold a JSON object")
        missing = {"version", "scheme", "n_docs", "default_idf", "idf", "sha256"} - set(payload)
        if missing:
            raise ValueError(f"IDF file is missing fields: {sorted(missing)}")
        if payload["version"] != IDF_FORMAT_VERSION or payload["scheme"] != IDF_SCHEME:
            raise ValueError("IDF file has an unsupported version or scheme")
        if not isinstance(payload["idf"], dict):
            raise TypeError("IDF file field 'idf' must be an object")
        try:
            loaded = cls.from_mapping(payload["n_docs"], payload["idf"], payload["default_idf"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"IDF file content is invalid: {exc}") from exc
        if payload["sha256"] != loaded.digest:
            raise ValueError("IDF file digest mismatch: the file was altered or is corrupt")
        return loaded

    @classmethod
    def load(cls, path: Path | str) -> FrozenIdf:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


class FeatureIndex:
    """Precomputed text vectors so scoring a pair costs microseconds.

    IDF is computed from the NC texts only (no labels) and frozen at build time. Pass a
    FrozenIdf as `idf` to use statistics fitted elsewhere (for example on the DEV split only)
    instead of fitting on `ncs`; tokens the statistics have not seen get their default_idf.
    """

    def __init__(self, ncs: Iterable[NC], *, idf: FrozenIdf | None = None) -> None:
        ncs = list(ncs)
        tfs = {nc.id: self._tf(nc) for nc in ncs}
        self._frozen = idf if idf is not None else fit_idf(ncs)
        self._idf = dict(self._frozen.idf)
        self._default_idf = self._frozen.default_idf
        self._docs: dict[str, Doc] = {nc.id: self._build(nc, tfs[nc.id]) for nc in ncs}

    # ---- building
    @staticmethod
    def _text(nc: NC) -> str:
        return f"{nc.title} {nc.description}"

    @classmethod
    def _tf(cls, nc: NC) -> dict[str, float]:
        counts = Counter(tokenize(cls._text(nc)))
        return {t: 1.0 + math.log(c) for t, c in counts.items()}

    def _build(self, nc: NC, tf: dict[str, float]) -> Doc:
        raw = {t: w * self._idf.get(t, self._default_idf) for t, w in tf.items()}
        norm = math.sqrt(sum(v * v for v in raw.values())) or 1.0
        text = self._text(nc)
        return Doc(
            nc=nc,
            vec={t: v / norm for t, v in raw.items()},
            grams=trigrams(text),
            concepts=frozenset(glossary.concepts_in(text)),
        )

    def upsert(self, nc: NC) -> None:
        """Add or refresh one NC without rebuilding IDF."""
        self._docs[nc.id] = self._build(nc, self._tf(nc))

    # ---- access
    @property
    def idf(self) -> FrozenIdf:
        """The frozen IDF statistics this index scores with."""
        return self._frozen

    @property
    def ids(self) -> list[str]:
        return list(self._docs)

    def __contains__(self, nc_id: object) -> bool:
        return nc_id in self._docs

    def nc(self, nc_id: str) -> NC:
        return self._docs[nc_id].nc

    # ---- features
    def pair_features(self, a_id: str, b_id: str) -> dict[str, float]:
        da, db = self._docs[a_id], self._docs[b_id]
        a, b = da.nc, db.nc
        days = abs((a.raised_at - b.raised_at).total_seconds()) / 86400.0
        return {
            "same_product": _same(a.product, b.product),
            "same_line": _same(a.line, b.line),
            "same_process": _same(a.process, b.process),
            "same_department": _same(a.department_id, b.department_id),
            "same_root_cause": _same(a.root_cause_category, b.root_cause_category),
            "same_defect_code": _same(a.defect_code, b.defect_code),
            "same_machine": _same(a.machine, b.machine),
            "same_lot": _same(a.lot, b.lot),
            "time_proximity": math.exp(-days / TIME_SCALE_DAYS),
            "tfidf_cosine": _dot(da.vec, db.vec),
            "char_similarity": _dice(da.grams, db.grams),
            "glossary_overlap": _jaccard(da.concepts, db.concepts),
        }

    def feature_matrix(self, pairs: Sequence[tuple[str, str]], names: Sequence[str]):
        import numpy as np

        out = np.empty((len(pairs), len(names)))
        for r, (a, b) in enumerate(pairs):
            f = self.pair_features(a, b)
            out[r] = [f[n] for n in names]
        return out

    def evidence(self, a_id: str, b_id: str, name: str, value: float) -> str:
        da, db = self._docs[a_id], self._docs[b_id]
        a, b = da.nc, db.nc
        if name == "same_product":
            return f"Both are {a.product}"
        if name == "same_line":
            return f"Both on {a.line}"
        if name == "same_process":
            return f"Both in {a.process}"
        if name == "same_department":
            return f"Both owned by {taxonomy.DEPARTMENTS.get(a.department_id, a.department_id)}"
        if name == "same_root_cause":
            rc = a.root_cause_category
            return f"Both root cause {rc}: {taxonomy.ROOT_CAUSE_CATEGORIES.get(rc, rc)}"
        if name == "same_defect_code":
            dc = a.defect_code
            return f"Both defect {dc}: {taxonomy.DEFECT_CODES.get(dc, dc)}"
        if name == "same_machine":
            return f"Both on machine {a.machine}"
        if name == "same_lot":
            return f"Both from lot {a.lot}"
        if name == "time_proximity":
            days = round(abs((a.raised_at - b.raised_at).total_seconds()) / 86400.0)
            return f"Raised {days} days apart ({a.raised_at:%d %b %Y} and {b.raised_at:%d %b %Y})"
        if name == "tfidf_cosine":
            shared = sorted(set(da.vec) & set(db.vec), key=lambda t: -(da.vec[t] * db.vec[t]))
            if shared:
                return "Shared wording: " + ", ".join(shared[:4])
            return "Similar wording"
        if name == "char_similarity":
            return f"{round(value * 100)}% character-level text overlap"
        if name == "glossary_overlap":
            shared_c = sorted(da.concepts & db.concepts)
            return "Same failure concept: " + ", ".join(c.replace("_", " ") for c in shared_c)
        return name


def fit_idf(ncs: Iterable[NC]) -> FrozenIdf:
    """Fit IDF statistics from NC texts only (no labels). Pure function of the given NCs.

    This is the formula FeatureIndex has always used: n counts the NCs given, document
    frequency counts each NC id once, and a token never seen gets ln(1 + n) + 1.
    """
    ncs = list(ncs)
    tfs = {nc.id: FeatureIndex._tf(nc) for nc in ncs}
    df: Counter = Counter()
    for tf in tfs.values():
        df.update(tf.keys())
    n = len(ncs)
    idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}
    return FrozenIdf.from_mapping(n, idf, math.log(1 + n) + 1.0)