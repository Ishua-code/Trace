"""Canonical lists for TRACE.

All names are SYNTHETIC demo data (no real company). This is the single source
of truth for seed/, the engine and the UI dropdowns. Stdlib only.
"""
from __future__ import annotations

PRODUCTS: tuple[str, ...] = (
    "Brake Drum",
    "Brake Disc",
    "Wheel Hub",
    "Steering Knuckle",
    "Axle Shaft",
    "Flywheel",
)

LINES: tuple[str, ...] = tuple(f"Line {i}" for i in range(1, 6))

# Department ids are PROPOSED; Ishwarya's DB seed must use the same ids.
DEPARTMENTS: dict[int, str] = {
    1: "Foundry",
    2: "Machining",
    3: "Heat Treatment",
    4: "Surface Coating",
    5: "Assembly",
    6: "Quality Assurance",
    7: "Maintenance & Tooling",
}

# process -> owning department id (feeds auto-assignment of NCs)
PROCESS_DEPARTMENT: dict[str, int] = {
    "Casting": 1,
    "CNC Turning": 2,
    "Bore Machining": 2,
    "Deburring": 2,
    "Grinding": 2,
    "Heat Treatment": 3,
    "Surface Coating": 4,
    "Assembly": 5,
    "Final Inspection": 6,
}
PROCESSES: tuple[str, ...] = tuple(PROCESS_DEPARTMENT)

# Stored value is the code; the UI shows the label.
ROOT_CAUSE_CATEGORIES: dict[str, str] = {
    "TOOL_LIFE": "Tool wear / tool life not controlled",
    "MACHINE_SETTING": "Machine setting or parameter drift",
    "MATERIAL": "Incoming material variation",
    "METHOD": "Work method or procedure gap",
    "MEASUREMENT": "Gauge or measurement error",
    "OPERATOR": "Operator skill or training",
    "FIXTURE": "Fixture or jig wear / misalignment",
    "HEAT_TREAT": "Heat treatment cycle deviation",
    "MAINTENANCE": "Preventive maintenance gap",
    "ENVIRONMENT": "Environment or handling damage",
}

DEFECT_CODES: dict[str, str] = {
    "DEF-BURR": "Burr / sharp edge / flash",
    "DEF-DIM": "Dimension out of tolerance",
    "DEF-CRACK": "Crack",
    "DEF-POROS": "Porosity / blow hole",
    "DEF-HARD": "Hardness out of spec",
    "DEF-FINISH": "Surface finish defect",
    "DEF-RUNOUT": "Runout / out of round",
    "DEF-COAT": "Coating defect",
    "DEF-DAMAGE": "Handling damage",
}


def validate_fields(
    product: str | None = None,
    line: str | None = None,
    process: str | None = None,
    root_cause: str | None = None,
    defect_code: str | None = None,
) -> list[str]:
    """Return a list of problems; empty list means every given field is canonical."""
    errors: list[str] = []
    if product is not None and product not in PRODUCTS:
        errors.append(f"unknown product: {product}")
    if line is not None and line not in LINES:
        errors.append(f"unknown line: {line}")
    if process is not None and process not in PROCESS_DEPARTMENT:
        errors.append(f"unknown process: {process}")
    if root_cause is not None and root_cause not in ROOT_CAUSE_CATEGORIES:
        errors.append(f"unknown root cause: {root_cause}")
    if defect_code is not None and defect_code not in DEFECT_CODES:
        errors.append(f"unknown defect code: {defect_code}")
    return errors