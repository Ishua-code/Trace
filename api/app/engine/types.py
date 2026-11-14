"""Engine-owned working types.

PROPOSED for contracts.py (needs Ishwarya's approval, see docs/contract-proposals.md).
Until then they live here so the engine and the UI mocks can move.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.contracts import NCStatus, Severity


class GraphNode(BaseModel):
    id: str
    title: str
    status: NCStatus
    severity: Severity
    product: str
    line: str | None = None
    cluster_id: str | None = None
    age_days: int


class GraphEdge(BaseModel):
    a: str
    b: str
    score: float
    link_id: int | None = None
    confirmed: bool | None = None


class FailurePath(BaseModel):
    source: str = Field(description="Closed or about-to-close NC")
    target: str = Field(description="Unresolved connected NC")
    hops: list[str] = Field(description="NC ids from source to target, inclusive")
    scores: list[float] = Field(description="Link score of each hop")


class Graph(BaseModel):
    focus_nc: str | None = None
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    clusters: dict[str, list[str]] = Field(default_factory=dict, description="cluster id -> NC ids")
    paths: list[FailurePath] = []
    footprint: dict[str, list[str]] = Field(
        default_factory=dict, description="keys: products, lines, processes, departments"
    )


class WeightUpdate(BaseModel):
    link_id: int
    confirmed: bool
    at: datetime
    before: dict[str, float]
    after: dict[str, float]