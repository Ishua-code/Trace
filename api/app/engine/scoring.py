"""Link scoring: weighted logistic combination of pair features, with explanations."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from app.contracts import Link, Signal
from app.engine.features import FeatureIndex
from app.engine.store import pair_key

WEIGHTS_PATH = Path(__file__).with_name("weights.json")


def _sigmoid(z: float) -> float:
    z = max(-35.0, min(35.0, z))
    return 1.0 / (1.0 + math.exp(-z))


@dataclass(frozen=True)
class FrozenWeights:
    bias: float
    weights: dict[str, float]
    threshold: float
    meta: dict = field(default_factory=dict)


def load_weights(path: Path | str | None = None) -> FrozenWeights:
    p = Path(path) if path else WEIGHTS_PATH
    if not p.exists():
        raise FileNotFoundError(f"{p} missing. Fit it with: python -m eval.fit_weights")
    raw = json.loads(p.read_text(encoding="utf-8"))
    return FrozenWeights(
        bias=float(raw["bias"]),
        weights={k: float(v) for k, v in raw["weights"].items()},
        threshold=float(raw["threshold"]),
        meta=raw.get("meta", {}),
    )


def save_weights(w: FrozenWeights, path: Path | str | None = None) -> None:
    p = Path(path) if path else WEIGHTS_PATH
    payload = {
        "version": 1,
        "bias": round(w.bias, 6),
        "threshold": round(w.threshold, 4),
        "weights": {k: round(v, 6) for k, v in w.weights.items()},
        "meta": w.meta,
    }
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class LinkScorer:
    """score = sigmoid(bias + sum(value * effective_weight)); effective = frozen + learned delta."""

    def __init__(
        self, index: FeatureIndex, weights: FrozenWeights, deltas: dict[str, float] | None = None
    ) -> None:
        self.index = index
        self.weights = weights
        self.deltas = dict(deltas or {})
        self._w = {n: w + self.deltas.get(n, 0.0) for n, w in weights.weights.items()}

    def _prob(self, feats: dict[str, float]) -> float:
        z = self.weights.bias
        for name, w in self._w.items():
            z += feats[name] * w
        return _sigmoid(z)

    def _build_link(self, a: str, b: str, feats: dict[str, float], prob: float) -> Link:
        signals = []
        for name, w in self._w.items():
            v = feats[name]
            if v <= 0.0:
                continue
            signals.append(Signal(
                name=name, value=round(v, 4), weight=round(w, 4), contribution=round(v * w, 4),
                evidence=self.index.evidence(a, b, name, v),
            ))
        signals.sort(key=lambda s: (-s.contribution, s.name))
        return Link(a=a, b=b, score=round(prob, 4), signals=signals)

    def score_pair(self, a_id: str, b_id: str) -> Link:
        a, b = pair_key(a_id, b_id)
        feats = self.index.pair_features(a, b)
        return self._build_link(a, b, feats, self._prob(feats))

    def related(self, nc_id: str, threshold: float | None = None) -> list[Link]:
        if nc_id not in self.index:
            raise KeyError(nc_id)
        thr = self.weights.threshold if threshold is None else threshold
        out: list[Link] = []
        for other in self.index.ids:
            if other == nc_id:
                continue
            a, b = pair_key(nc_id, other)
            feats = self.index.pair_features(a, b)
            p = self._prob(feats)
            if p >= thr:
                out.append(self._build_link(a, b, feats, p))
        out.sort(key=lambda l: (-l.score, l.a, l.b))
        return out

    def all_links(self, threshold: float | None = None) -> dict[str, list[Link]]:
        """Every link at or above the threshold, grouped under both of its NCs."""
        thr = self.weights.threshold if threshold is None else threshold
        ids = sorted(self.index.ids)
        out: dict[str, list[Link]] = {i: [] for i in ids}
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                feats = self.index.pair_features(a, b)
                p = self._prob(feats)
                if p >= thr:
                    link = self._build_link(a, b, feats, p)
                    out[a].append(link)
                    out[b].append(link)
        for links in out.values():
            links.sort(key=lambda l: (-l.score, l.a, l.b))
        return out