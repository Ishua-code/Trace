"""Domain glossary: maps differently worded text to shared concepts.

Used by link scoring so "burr", "sharp edge" and "flash" count as the same
thing even when two NCs share no keywords. Stdlib only.
"""
from __future__ import annotations

import re

# Phrases are written lowercase; hyphens/underscores/slashes count as spaces.
GLOSSARY: dict[str, list[str]] = {
    "burr": [
        "burr", "burrs", "sharp edge", "sharp edges", "flash", "raised lip",
        "rough edge", "edge roughness", "unfinished edge",
    ],
    "tool_wear": [
        "tool wear", "worn tool", "worn insert", "blunt tool", "dull tool",
        "tool life", "tool change", "tool changed", "tool replacement",
        "insert replacement",
    ],
    "out_of_tolerance": [
        "out of tolerance", "oot", "oversize", "undersize", "off size",
        "dimension deviation", "bore diameter deviation",
    ],
    "crack": ["crack", "cracks", "cracking", "hairline crack", "fracture"],
    "porosity": [
        "porosity", "blow hole", "blowhole", "gas hole", "pinhole",
        "shrinkage cavity",
    ],
    "low_hardness": [
        "low hardness", "soft spot", "hardness below", "hardness deviation",
        "under hardened", "insufficient hardness",
    ],
    "surface_finish": [
        "rough surface", "surface roughness", "poor finish", "scratch",
        "scoring", "tool marks", "chatter", "chatter marks",
    ],
    "runout": ["runout", "run out", "wobble", "eccentricity", "out of round", "ovality"],
    "coating_fault": [
        "paint peel", "coating peel", "flaking", "poor adhesion",
        "coating thickness", "uneven coating",
    ],
    "gauge_issue": [
        "gauge error", "calibration overdue", "instrument drift",
        "measurement variation", "unverified gauge",
    ],
    "undefined_control": [
        "not tracked", "no tracking", "no record", "undefined interval",
        "interval undefined", "not defined", "no counter",
        "no tool life tracking", "no monitoring",
    ],
}


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[-_/]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _compile(phrases: list[str]) -> re.Pattern[str]:
    ordered = sorted({_normalize(p) for p in phrases}, key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(re.escape(p) for p in ordered) + r")\b")


_PATTERNS: dict[str, re.Pattern[str]] = {
    concept: _compile(phrases) for concept, phrases in GLOSSARY.items()
}


def concepts_in(text: str) -> set[str]:
    """Return the set of glossary concepts mentioned in text."""
    norm = _normalize(text)
    return {c for c, pat in _PATTERNS.items() if pat.search(norm)}


def augment_text(text: str) -> str:
    """Append concept tokens so TF-IDF sees synonyms as shared words."""
    tokens = " ".join(f"concept_{c}" for c in sorted(concepts_in(text)))
    return f"{text} {tokens}".strip()