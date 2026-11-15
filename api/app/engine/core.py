"""TraceEngine implementation. Methods are filled in step by step."""
from __future__ import annotations

from pathlib import Path

from app.contracts import ClosureReport, Link, Recommendation
from app.engine.clock import Clock, SystemClock
from app.engine.features import FeatureIndex, FrozenIdf
from app.engine.scoring import FrozenWeights, LinkScorer, load_weights
from app.engine.store import NCStore

IDF_PATH = Path(__file__).with_name("idf.json")
class TraceEngineImpl:
    def __init__(
        self, store: NCStore, clock: Clock | None = None, weights: FrozenWeights | None = None
    ) -> None:
        self.store = store
        self.clock = clock or SystemClock()
        self._weights = weights
        self._index: FeatureIndex | None = None

    def refresh_index(self) -> None:
        """Rebuild text vectors using the frozen DEV IDF when required."""
        if self._weights is None:
            self._weights = load_weights()

        expected_hash = self._weights.meta.get("dev_idf_sha256")

        if expected_hash:
            if not IDF_PATH.exists():
                raise FileNotFoundError(
                    f"Frozen DEV IDF not found: {IDF_PATH}"
                )

            idf = FrozenIdf.load(IDF_PATH)

            if idf.digest != expected_hash:
                raise ValueError(
                    "Frozen IDF hash does not match the model weights."
                )

            self._index = FeatureIndex(self.store.list_ncs(), idf=idf)
        else:
            self._index = FeatureIndex(self.store.list_ncs())

    def _scorer(self) -> LinkScorer:
        if self._weights is None:
            self._weights = load_weights()

        if self._index is None:
            self.refresh_index()

        return LinkScorer(
            self._index,
            self._weights,
            self.store.get_weight_deltas(),
        )
    def index_nc(self, nc_id: str) -> list[Link]:
        """Compute and store all links for one NC (call on NC create/update)."""
        nc = self.store.get_nc(nc_id)
        if nc is None:
            raise KeyError(nc_id)
        if self._index is None:
            self.refresh_index()
        else:
            self._index.upsert(nc)
        return self.store.save_links(nc_id, self._scorer().related(nc_id))

    def index_all(self) -> int:
        """Compute and store links for every NC. Returns the number of unique links."""
        self.refresh_index()
        grouped = self._scorer().all_links()
        for nc_id, links in grouped.items():
            self.store.save_links(nc_id, links)
        return sum(len(v) for v in grouped.values()) // 2

    def find_related(self, nc_id: str) -> list[Link]:
        if self.store.get_nc(nc_id) is None:
            raise KeyError(nc_id)
        return self.store.get_links(nc_id)

    def simulate_closure(self, nc_id: str) -> ClosureReport:
        raise NotImplementedError("Step 8: rules and verdict")

    def plan_risk(self, month: str) -> list[Recommendation]:
        raise NotImplementedError("Step 11: risk-adaptive planner")

    def record_feedback(self, link_id: int, confirmed: bool) -> None:
        raise NotImplementedError("Step 11: learning loop")