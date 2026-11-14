"""TraceEngine implementation. Methods are filled in step by step."""
from __future__ import annotations

from app.contracts import ClosureReport, Link, Recommendation
from app.engine.clock import Clock, SystemClock
from app.engine.store import NCStore


class TraceEngineImpl:
    def __init__(self, store: NCStore, clock: Clock | None = None) -> None:
        self.store = store
        self.clock = clock or SystemClock()

    def index_nc(self, nc_id: str) -> list[Link]:
        raise NotImplementedError("Step 6: link scoring")

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