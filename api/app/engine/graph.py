"""Failure graph around one NC: linked NCs, failure paths and the affected footprint.

Built only from links that are already stored (Step 6), so no scoring happens here.

* Links an auditor rejected (confirmed is False) are drawn but never used to reach an NC.
  Unreviewed links (confirmed is None) and confirmed links are used.
* A failure path runs from the focus NC to an unresolved NC. It may pass through closed NCs.
  Among all paths of at most `max_hops` links the strongest one is kept, where strength is the
  product of the link scores. Ties go to fewer hops, then to the lower NC ids.
* Linked groups are connected components of the drawn graph. They are a connectivity view, not
  confirmed clusters: a few false links can join unrelated NCs.
"""
from __future__ import annotations

import math
from datetime import datetime
from itertools import pairwise

import networkx as nx

from app.contracts import NC, Link
from app.engine.store import NCStore, is_unresolved
from app.engine.taxonomy import DEPARTMENTS
from app.engine.types import FailurePath, Graph, GraphEdge, GraphNode

DEFAULT_MAX_HOPS = 2
MAX_HOPS_LIMIT = 4


def _other(link: Link, nc_id: str) -> str:
    return link.b if link.a == nc_id else link.a


def _usable(link: Link) -> bool:
    return link.confirmed is not False


def build_graph(
    store: NCStore, focus: str, now: datetime, max_hops: int = DEFAULT_MAX_HOPS
) -> Graph:
    if not 1 <= max_hops <= MAX_HOPS_LIMIT:
        raise ValueError(f"max_hops must be between 1 and {MAX_HOPS_LIMIT}")
    ncs: dict[str, NC] = {nc.id: nc for nc in store.list_ncs()}
    if focus not in ncs:
        raise KeyError(focus)

    # Breadth-first walk over usable links, at most max_hops links from the focus.
    depth = {focus: 0}
    links: dict[tuple[str, str], Link] = {}
    queue = [focus]
    while queue:
        nxt: list[str] = []
        for nc_id in queue:
            for link in sorted(store.get_links(nc_id), key=lambda x: (x.a, x.b)):
                if not _usable(link) or link.a not in ncs or link.b not in ncs:
                    continue
                if depth[nc_id] >= max_hops and _other(link, nc_id) not in depth:
                    continue
                other = _other(link, nc_id)
                if other not in depth:
                    depth[other] = depth[nc_id] + 1
                    nxt.append(other)
                links[(link.a, link.b)] = link
        queue = nxt

    # Edges between reached NCs, including rejected ones so the UI can show them struck out.
    for nc_id in sorted(depth):
        for link in store.get_links(nc_id):
            if link.a in depth and link.b in depth:
                links.setdefault((link.a, link.b), link)

    g = nx.Graph()
    g.add_nodes_from(sorted(depth))
    for (a, b), link in sorted(links.items()):
        g.add_edge(a, b, score=link.score, usable=_usable(link))

    usable = nx.Graph()
    usable.add_nodes_from(g.nodes)
    usable.add_edges_from((a, b) for a, b, d in g.edges(data=True) if d["usable"])

    clusters: dict[str, list[str]] = {}
    cluster_of: dict[str, str] = {}
    groups = sorted((sorted(c) for c in nx.connected_components(usable) if len(c) > 1),
                    key=lambda c: (-len(c), c[0]))
    for i, members in enumerate(groups, start=1):
        clusters[f"G{i}"] = members
        for m in members:
            cluster_of[m] = f"G{i}"

    paths = _failure_paths(usable, g, ncs, focus, max_hops)

    affected = [ncs[focus]] + [ncs[p.target] for p in paths]
    footprint = {
        "products": sorted({n.product for n in affected}),
        "lines": sorted({n.line for n in affected if n.line}),
        "processes": sorted({n.process for n in affected}),
        "departments": sorted({DEPARTMENTS.get(n.department_id, str(n.department_id))
                               for n in affected}),
    }

    nodes = [
        GraphNode(
            id=i, title=ncs[i].title, status=ncs[i].status, severity=ncs[i].severity,
            product=ncs[i].product, line=ncs[i].line, cluster_id=cluster_of.get(i),
            age_days=max(0, (now - ncs[i].raised_at).days),
        )
        for i in sorted(depth)
    ]
    edges = [
        GraphEdge(a=a, b=b, score=l.score, link_id=l.id, confirmed=l.confirmed)
        for (a, b), l in sorted(links.items())
    ]
    return Graph(focus_nc=focus, nodes=nodes, edges=edges, clusters=clusters,
                 paths=paths, footprint=footprint)


def _failure_paths(
    usable: nx.Graph, g: nx.Graph, ncs: dict[str, NC], focus: str, max_hops: int
) -> list[FailurePath]:
    best: dict[str, tuple[float, int, list[str]]] = {}
    for target in sorted(usable.nodes):
        if target == focus or not is_unresolved(ncs[target]):
            continue
        for hops in nx.all_simple_paths(usable, focus, target, cutoff=max_hops):
            scores = [g[u][v]["score"] for u, v in pairwise(hops)]
            strength = math.prod(scores)
            key = (-strength, len(hops), hops)
            if target not in best or key < (-best[target][0], best[target][1], best[target][2]):
                best[target] = (strength, len(hops), hops)
    out = []
    for target, (strength, _, hops) in best.items():
        scores = [g[u][v]["score"] for u, v in pairwise(hops)]
        out.append((strength, FailurePath(source=focus, target=target, hops=hops, scores=scores)))
    out.sort(key=lambda t: (-t[0], t[1].target))
    return [p for _, p in out]