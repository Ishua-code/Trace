from app.engine import glossary as g
from app.engine import taxonomy as t


def test_canonical_counts():
    assert len(t.PRODUCTS) == 6
    assert len(t.LINES) == 5
    assert len(t.DEPARTMENTS) == 7


def test_no_duplicates():
    for items in (t.PRODUCTS, t.LINES, t.PROCESSES):
        assert len(items) == len(set(items))


def test_every_process_has_a_real_department():
    assert set(t.PROCESS_DEPARTMENT.values()) <= set(t.DEPARTMENTS)


def test_validate_fields():
    assert t.validate_fields("Brake Drum", "Line 2", "Deburring", "TOOL_LIFE", "DEF-BURR") == []
    assert len(t.validate_fields(product="Spaceship", line="Line 9")) == 2


def test_synonyms_unique_across_concepts():
    seen: dict[str, str] = {}
    for concept, phrases in g.GLOSSARY.items():
        for p in phrases:
            key = g._normalize(p)
            assert key not in seen, f"{key!r} in {concept} and {seen[key]}"
            seen[key] = concept


def test_golden_wording_shares_a_concept():
    a = g.concepts_in("Burr found on brake drum bore at Line 2")
    b = g.concepts_in("Sharp edge observed on machined surface, Line 4")
    assert "burr" in a and "burr" in b


def test_undefined_control_detected():
    text = "Tool change interval undefined; no tool-life tracking"
    found = g.concepts_in(text)
    assert {"tool_wear", "undefined_control"} <= found


def test_augment_adds_tokens():
    assert "concept_burr" in g.augment_text("sharp edge on bore")
    assert g.augment_text("nothing relevant here") == "nothing relevant here"