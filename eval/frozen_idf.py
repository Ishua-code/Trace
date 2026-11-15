"""Fit the frozen IDF statistics on the DEV split only. Offline use.

IDF is label-free, but the TEST and GOLDEN texts must still not shape it: they are the data the
model is judged on, and the runtime has to apply the very statistics the weights were fitted with.
Nothing here writes a file unless asked: `idf.json` is only produced at the final refreeze.

    python -m eval.frozen_idf --out <path>      # explicit path, there is no default
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

_API = str(Path(__file__).resolve().parents[1] / "api")
if _API not in sys.path:
    sys.path.insert(0, _API)

from app.contracts import NC
from app.engine.features import FrozenIdf, fit_idf

DEV = "dev"


def dev_ncs(data: dict) -> list[NC]:
    """The DEV NCs of a generated seed, in their original order."""
    splits = data["ground_truth"]["splits"]
    ncs = list(data["ncs"])
    unknown = sum(1 for nc in ncs if nc.id not in splits)
    if unknown:
        raise ValueError(f"{unknown} NC(s) have no split label; refusing to guess")
    return [nc for nc in ncs if splits[nc.id] == DEV]


def dev_ids_digest(ncs: list[NC]) -> str:
    """SHA-256 of the sorted NC ids, to record which NCs the statistics were fitted on."""
    blob = "\n".join(sorted(nc.id for nc in ncs))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def fit_dev_idf(data: dict, ncs: list[NC] | None = None) -> FrozenIdf:
    """Fit IDF on DEV NCs only.

    With no `ncs`, the DEV NCs are taken from the seed. When `ncs` is given it is checked, not
    trusted: any NC that is not DEV (or has no split label), a duplicate id, or an empty list
    raises ValueError.
    """
    splits = data["ground_truth"]["splits"]
    chosen = dev_ncs(data) if ncs is None else list(ncs)
    if not chosen:
        raise ValueError("no NCs to fit IDF on")
    ids = [nc.id for nc in chosen]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate NC ids in the IDF fitting set")
    bad = [splits.get(i, "unlabelled") for i in ids if splits.get(i) != DEV]
    if bad:
        kinds = ", ".join(sorted(set(bad)))
        raise ValueError(f"non-dev NCs rejected: {len(bad)} NC(s) from split(s) {kinds}")
    return fit_idf(chosen)


def write_dev_idf(data: dict, path: Path | str) -> FrozenIdf:
    """Fit on DEV and save to `path`. The caller chooses the path; nothing is written elsewhere."""
    idf = fit_dev_idf(data)
    idf.save(path)
    return idf


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Fit and save DEV-only frozen IDF statistics")
    parser.add_argument("--out", required=True, help="where to write the IDF json")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    from seed.generate import generate

    data = generate(args.seed)
    idf = write_dev_idf(data, args.out)
    print(f"wrote {args.out}: {idf}")
    print(f"dev ids sha256: {dev_ids_digest(dev_ncs(data))}")


if __name__ == "__main__":
    main()