"""Hand-written hard cases for TRACE evaluation (SYNTHETIC demo data).

40 NC pairs, EVALUATION ONLY: never used to fit weights or tune rules.
Each pair has `label` (should TRACE link them?) and `needs`, the signal that
should resolve it:
  glossary - same concept in different words; structure is weak (rc unset)
  structure - unrelated wording; same machine/lot/root cause carries it
  both      - synonym text AND shared machine/lot
  decoy     - hard negative: same product/line/machine/lot, different cause
All 80 NCs use ids HC-NN-A / HC-NN-B so they never collide with the main seed.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

_API = Path(__file__).resolve().parents[1] / "api"
if str(_API) not in sys.path:
    sys.path.insert(0, str(_API))

GENERIC_WORDS = frozenset(
    ["the", "and", "with", "for", "was", "were", "are", "been", "has", "had", "not", "but", "from", "that", "this", "into", "onto", "over", "under", "after", "before", "during", "when", "while", "than", "then", "there", "their", "its", "can", "may", "one", "two", "all", "any", "per", "off", "out", "via", "also", "found", "noted", "observed", "seen", "audit", "check", "line", "lot", "part", "unit", "product", "brake", "drum", "disc", "wheel", "hub", "steering", "knuckle", "axle", "shaft", "flywheel"]
)

# (title, description, product, line, process, machine, lot, defect, root_cause, raised, status)
PAIRS: list[tuple[str, str, bool, tuple, tuple]] = [
    # ---- glossary: synonyms, weak structure (same product + defect code only)
    ("HC-01", "glossary", True,
     ("Burr on bore", "Burr left in bore after finishing pass.", "Brake Drum", "Line 2", "Bore Machining", "BM-02", "L2-2301", "DEF-BURR", None, "2026-05-04", "CLOSED"),
     ("Sharp edge on mounting face", "Sharp edge felt when gauge slid over seat.", "Brake Drum", "Line 4", "CNC Turning", "CT-04", "L4-2330", "DEF-BURR", None, "2026-06-15", "IN_PROGRESS")),
    ("HC-02", "glossary", True,
     ("Flash on casting seam", "Flash remained along seam after trimming.", "Steering Knuckle", "Line 1", "Casting", "CA-01", "L1-2305", "DEF-BURR", None, "2026-04-06", "CLOSED"),
     ("Burrs at keyway", "Burrs snagged operator gloves near slot.", "Steering Knuckle", "Line 3", "Deburring", "DB-03", "L3-2321", "DEF-BURR", None, "2026-05-20", "IN_PROGRESS")),
    ("HC-03", "glossary", True,
     ("Worn insert on finishing pass", "Worn insert left chatter-like streaks across surface.", "Axle Shaft", "Line 2", "CNC Turning", "CT-02", "L2-2310", "DEF-FINISH", None, "2026-03-09", "CLOSED"),
     ("Dull tool noticed", "Dull tool kept running beyond planned swap.", "Axle Shaft", "Line 5", "Grinding", "GR-05", "L5-2344", "DEF-FINISH", None, "2026-04-27", "IN_PROGRESS")),
    ("HC-04", "glossary", True,
     ("Blow hole in casting", "Blow hole opened up after cutting.", "Flywheel", "Line 1", "Casting", "CA-01", "L1-2312", "DEF-POROS", None, "2026-02-16", "CLOSED"),
     ("Pinhole on machined face", "Pinhole spotted along sealing land.", "Flywheel", "Line 2", "CNC Turning", "CT-02", "L2-2340", "DEF-POROS", None, "2026-04-13", "IN_PROGRESS")),
    ("HC-05", "glossary", True,
     ("Hairline crack at web", "Hairline crack picked up by dye test.", "Wheel Hub", "Line 3", "Casting", "CA-03", "L3-2315", "DEF-CRACK", None, "2026-01-12", "CLOSED"),
     ("Fracture on flange", "Fracture surfaced during destructive sampling.", "Wheel Hub", "Line 1", "Final Inspection", "GA-01", "L1-2350", "DEF-CRACK", None, "2026-03-23", "IN_PROGRESS")),
    ("HC-06", "glossary", True,
     ("Runout beyond limit", "Runout exceeded drawing limit on mandrel.", "Brake Disc", "Line 4", "Bore Machining", "BM-04", "L4-2318", "DEF-RUNOUT", None, "2026-02-02", "CLOSED"),
     ("Wobble on test rig", "Wobble visible when spun on rig fixture.", "Brake Disc", "Line 2", "Final Inspection", "GA-02", "L2-2352", "DEF-RUNOUT", None, "2026-04-06", "IN_PROGRESS")),
    ("HC-07", "glossary", True,
     ("Soft spot on journal", "Soft spot found by file test.", "Axle Shaft", "Line 5", "Heat Treatment", "HT-05", "L5-2320", "DEF-HARD", None, "2026-03-02", "CLOSED"),
     ("Hardness below specification", "Hardness below minimum across tray sample.", "Axle Shaft", "Line 3", "Heat Treatment", "HT-03", "L3-2355", "DEF-HARD", None, "2026-04-20", "IN_PROGRESS")),
    ("HC-08", "glossary", True,
     ("Paint peel on flange", "Paint peel after salt spray.", "Wheel Hub", "Line 5", "Surface Coating", "SC-05", "L5-2322", "DEF-COAT", None, "2026-02-09", "CLOSED"),
     ("Poor adhesion on face", "Poor adhesion shown by tape pull.", "Wheel Hub", "Line 2", "Surface Coating", "SC-02", "L2-2358", "DEF-COAT", None, "2026-04-13", "IN_PROGRESS")),
    ("HC-09", "glossary", True,
     ("Calibration overdue on micrometer", "Calibration overdue sticker expired last month.", "Brake Drum", "Line 2", "Final Inspection", "GA-02", "L2-2324", "DEF-DIM", None, "2026-01-19", "CLOSED"),
     ("Instrument drift suspected", "Instrument drift suspected from master mismatch.", "Brake Drum", "Line 4", "Final Inspection", "GA-04", "L4-2360", "DEF-DIM", None, "2026-03-16", "IN_PROGRESS")),
    ("HC-10", "glossary", True,
     ("Chatter marks on web", "Chatter marks visible under raking light.", "Flywheel", "Line 3", "Grinding", "GR-03", "L3-2326", "DEF-FINISH", None, "2026-02-23", "CLOSED"),
     ("Scratch on face", "Scratch lengthwise along sealing area.", "Flywheel", "Line 1", "Grinding", "GR-01", "L1-2362", "DEF-FINISH", None, "2026-04-27", "IN_PROGRESS")),
    ("HC-11", "glossary", True,
     ("No counter fitted", "No counter fitted on spindle, usage unknown.", "Steering Knuckle", "Line 4", "CNC Turning", "CT-04", "L4-2328", "DEF-FINISH", None, "2026-01-26", "CLOSED"),
     ("Not tracked in control plan", "Not tracked anywhere in control plan revision.", "Steering Knuckle", "Line 2", "Bore Machining", "BM-02", "L2-2364", "DEF-FINISH", None, "2026-03-30", "IN_PROGRESS")),
    # ---- structure: unrelated wording, same machine/lot/root cause
    ("HC-12", "structure", True,
     ("Edge snag complaint from assembly", "Fitters complained about snagging when handling machined parts.", "Brake Drum", "Line 2", "Bore Machining", "BM-02", "L2-2307", "DEF-BURR", "TOOL_LIFE", "2026-09-07", "CLOSED"),
     ("Insert swap missed on night shift", "Planned swap skipped; cutter ran extra hours.", "Brake Drum", "Line 2", "Bore Machining", "BM-02", "L2-2307", "DEF-BURR", "TOOL_LIFE", "2026-09-21", "IN_PROGRESS")),
    ("HC-13", "structure", True,
     ("Locating pad shows polish marks", "Contact pad looks shiny where parts seat.", "Axle Shaft", "Line 3", "CNC Turning", "CT-03", "L3-2331", "DEF-RUNOUT", "FIXTURE", "2026-08-03", "CLOSED"),
     ("Size drifting between consecutive pieces", "Consecutive pieces vary by several microns.", "Axle Shaft", "Line 3", "CNC Turning", "CT-03", "L3-2331", "DEF-DIM", "FIXTURE", "2026-08-17", "IN_PROGRESS")),
    ("HC-14", "structure", True,
     ("Supplier certificate mismatch", "Mill certificate shows different alloy percentages.", "Steering Knuckle", "Line 1", "Casting", "CA-01", "L1-2218", "DEF-CRACK", "MATERIAL", "2026-06-01", "CLOSED"),
     ("Fragments broke during press fitting", "Fragments broke under modest load at pressing.", "Steering Knuckle", "Line 1", "Assembly", "AS-01", "L1-2218", "DEF-CRACK", "MATERIAL", "2026-06-29", "IN_PROGRESS")),
    ("HC-15", "structure", True,
     ("Furnace recorder trace flat for ten minutes", "Recorder pen stayed level through soak segment.", "Axle Shaft", "Line 5", "Heat Treatment", "HT-05", "L5-2335", "DEF-HARD", "HEAT_TREAT", "2026-07-06", "CLOSED"),
     ("Batch failed acceptance on rockwell", "Rockwell readings low on three pieces from tray.", "Axle Shaft", "Line 5", "Heat Treatment", "HT-05", "L5-2335", "DEF-HARD", "HEAT_TREAT", "2026-07-13", "IN_PROGRESS")),
    ("HC-16", "structure", True,
     ("New joiner ran machine alone on second shift", "Trainee worked solo without sign off sheet.", "Flywheel", "Line 2", "Grinding", "GR-02", "L2-2338", "DEF-DAMAGE", "OPERATOR", "2026-08-10", "CLOSED"),
     ("Wrong tray used for finished goods", "Finished goods dropped into scrap tray by mistake.", "Flywheel", "Line 2", "Grinding", "GR-02", "L2-2338", "DEF-DAMAGE", "OPERATOR", "2026-08-12", "IN_PROGRESS")),
    ("HC-17", "structure", True,
     ("Coolant concentration low at grinder", "Refractometer reading under target for a week.", "Brake Disc", "Line 3", "Grinding", "GR-03", "L3-2342", "DEF-FINISH", "MAINTENANCE", "2026-05-11", "CLOSED"),
     ("Spindle noise reported by operator", "Bearing sound louder than usual at high rpm.", "Brake Disc", "Line 3", "Grinding", "GR-03", "L3-2342", "DEF-FINISH", "MAINTENANCE", "2026-05-25", "IN_PROGRESS")),
    ("HC-18", "structure", True,
     ("Torque step missing from instruction sheet", "Instruction omits tightening sequence for cover bolts.", "Wheel Hub", "Line 4", "Assembly", "AS-04", "L4-2346", "DEF-DAMAGE", "METHOD", "2026-06-08", "CLOSED"),
     ("Gasket fitted dry on two assemblies", "Seal installed without sealant as procedure unclear.", "Wheel Hub", "Line 4", "Assembly", "AS-04", "L4-2346", "DEF-DAMAGE", "METHOD", "2026-06-15", "IN_PROGRESS")),
    ("HC-19", "structure", True,
     ("Parts left uncovered over weekend", "Pallet stood open near the dock door.", "Brake Drum", "Line 5", "Final Inspection", "GA-05", "L5-2348", "DEF-DAMAGE", "ENVIRONMENT", "2026-07-20", "CLOSED"),
     ("Orange spots appeared on stored pieces", "Rust bloom noticed on finished units in rack.", "Brake Drum", "Line 5", "Final Inspection", "GA-05", "L5-2348", "DEF-DAMAGE", "ENVIRONMENT", "2026-07-27", "IN_PROGRESS")),
    ("HC-20", "structure", True,
     ("Master ring has visible nick", "Setting master carries nick near zero position.", "Axle Shaft", "Line 1", "Final Inspection", "GA-01", "L1-2351", "DEF-DIM", "MEASUREMENT", "2026-08-17", "CLOSED"),
     ("Operators reading differ by shift", "Day and night readings disagree on same specimen.", "Axle Shaft", "Line 1", "Final Inspection", "GA-01", "L1-2351", "DEF-DIM", "MEASUREMENT", "2026-08-24", "IN_PROGRESS")),
    ("HC-21", "structure", True,
     ("Surface looks hazy on the last pieces of shift", "Hazy finish started halfway through the second half.", "Steering Knuckle", "Line 4", "CNC Turning", "CT-04", "L4-2354", "DEF-FINISH", "TOOL_LIFE", "2026-09-14", "CLOSED"),
     ("Cutter edge chipped when removed", "Tip chipped on removal after a long run.", "Steering Knuckle", "Line 4", "CNC Turning", "CT-04", "L4-2357", "DEF-FINISH", "TOOL_LIFE", "2026-09-17", "IN_PROGRESS")),
    ("HC-22", "structure", True,
     ("Offset entered wrongly after changeover", "Wrong tool offset keyed in after job switch.", "Brake Disc", "Line 1", "CNC Turning", "CT-01", "L1-2359", "DEF-DIM", "MACHINE_SETTING", "2026-09-28", "CLOSED"),
     ("Diameter running large through the afternoon", "Diameter trend moved upward by 0.04 mm after lunch.", "Brake Disc", "Line 1", "CNC Turning", "CT-01", "L1-2359", "DEF-DIM", "MACHINE_SETTING", "2026-09-29", "IN_PROGRESS")),
    ("HC-23", "structure", True,
     ("Clamp pressure gauge reads erratic", "Hydraulic clamp needle jumps between values.", "Wheel Hub", "Line 2", "Bore Machining", "BM-02", "L2-2366", "DEF-RUNOUT", "FIXTURE", "2026-08-31", "CLOSED"),
     ("Pieces moving slightly in the chuck", "Slight movement in chuck jaws noticed under load.", "Wheel Hub", "Line 2", "Bore Machining", "BM-02", "L2-2366", "DEF-RUNOUT", "FIXTURE", "2026-09-08", "IN_PROGRESS")),
    ("HC-24", "structure", True,
     ("Billet end shows dark streak", "Dark streak on billet cross section after sawing.", "Axle Shaft", "Line 1", "CNC Turning", "CT-01", "L1-2201", "DEF-CRACK", "MATERIAL", "2026-05-05", "CLOSED"),
     ("Chips look different from usual", "Swarf colour changed and tool noise rose on this heat.", "Axle Shaft", "Line 1", "CNC Turning", "CT-01", "L1-2201", "DEF-FINISH", "MATERIAL", "2026-05-12", "IN_PROGRESS")),
    ("HC-25", "structure", True,
     ("Quench oil smells burnt", "Burnt odour from the quench tank this week.", "Flywheel", "Line 3", "Heat Treatment", "HT-03", "L3-2368", "DEF-HARD", "HEAT_TREAT", "2026-06-22", "CLOSED"),
     ("Case profile shallow on sectioned sample", "Microscope shows shallow case at the sectioned edge.", "Flywheel", "Line 3", "Heat Treatment", "HT-03", "L3-2368", "DEF-HARD", "HEAT_TREAT", "2026-06-29", "IN_PROGRESS")),
    # ---- both: synonym text AND shared machine/lot
    ("HC-26", "both", True,
     ("Burr near keyway", "Burr snagged glove at keyway slot.", "Steering Knuckle", "Line 3", "Deburring", "DB-03", "L3-2370", "DEF-BURR", "TOOL_LIFE", "2026-07-13", "CLOSED"),
     ("Rough edge at spline", "Rough edge noticed at spline end by assembler.", "Steering Knuckle", "Line 3", "Deburring", "DB-03", "L3-2370", "DEF-BURR", "TOOL_LIFE", "2026-07-20", "IN_PROGRESS")),
    ("HC-27", "both", True,
     ("Gas hole exposed on seat", "Gas hole exposed after skim.", "Flywheel", "Line 1", "Casting", "CA-01", "L1-2372", "DEF-POROS", "MATERIAL", "2026-04-20", "CLOSED"),
     ("Shrinkage cavity inside flange", "Shrinkage cavity showed during xray cut.", "Flywheel", "Line 1", "Casting", "CA-01", "L1-2372", "DEF-POROS", "MATERIAL", "2026-04-27", "IN_PROGRESS")),
    ("HC-28", "both", True,
     ("Flaking near bolt circle", "Flaking along bolt circle after cure oven.", "Wheel Hub", "Line 2", "Surface Coating", "SC-02", "L2-2374", "DEF-COAT", "METHOD", "2026-05-18", "CLOSED"),
     ("Uneven coating at rim", "Uneven coating thickness across rim region.", "Wheel Hub", "Line 2", "Surface Coating", "SC-02", "L2-2374", "DEF-COAT", "METHOD", "2026-05-25", "IN_PROGRESS")),
    # ---- decoy: hard negatives (same product/line/machine/lot, different cause)
    ("HC-29", "decoy", False,
     ("Burr beside keyway", "Burr snagged glove near slot.", "Brake Drum", "Line 2", "Bore Machining", "BM-02", "L2-2307", "DEF-BURR", "TOOL_LIFE", "2026-09-07", "CLOSED"),
     ("Calibration sticker expired", "Calibration overdue for pin gauge set.", "Brake Drum", "Line 2", "Bore Machining", "BM-02", "L2-2307", "DEF-DIM", "MEASUREMENT", "2026-09-08", "IN_PROGRESS")),
    ("HC-30", "decoy", False,
     ("Crack at web", "Crack noticed on web after quench.", "Wheel Hub", "Line 3", "Final Inspection", "GA-03", "L3-2376", "DEF-CRACK", "HEAT_TREAT", "2026-08-03", "CLOSED"),
     ("Flaking on rim", "Flaking along rim edge.", "Wheel Hub", "Line 3", "Final Inspection", "GA-03", "L3-2376", "DEF-COAT", "MATERIAL", "2026-08-05", "IN_PROGRESS")),
    ("HC-31", "decoy", False,
     ("Chatter marks on face", "Chatter marks under raking light.", "Axle Shaft", "Line 4", "Grinding", "GR-04", "L4-2378", "DEF-FINISH", "TOOL_LIFE", "2026-09-14", "CLOSED"),
     ("Dent from forklift forks", "Dent on rim from careless pallet handling.", "Axle Shaft", "Line 4", "Grinding", "GR-04", "L4-2378", "DEF-DAMAGE", "OPERATOR", "2026-09-15", "IN_PROGRESS")),
    ("HC-32", "decoy", False,
     ("Oversize bore reading", "Oversize noticed at hourly sample.", "Brake Disc", "Line 5", "Bore Machining", "BM-05", "L5-2380", "DEF-DIM", "MACHINE_SETTING", "2026-06-01", "CLOSED"),
     ("Housekeeping lapse near station", "Oil puddle and loose packaging around station floor.", "Brake Disc", "Line 5", "Bore Machining", "BM-05", "L5-2380", "DEF-DAMAGE", "ENVIRONMENT", "2026-06-02", "IN_PROGRESS")),
    ("HC-33", "decoy", False,
     ("Soft spot found near hole", "Soft spot on file test near mounting hole.", "Flywheel", "Line 2", "Heat Treatment", "HT-02", "L2-2382", "DEF-HARD", "HEAT_TREAT", "2026-07-06", "CLOSED"),
     ("Pyrometer certificate lapsed", "Pyrometer certificate lapsed last quarter.", "Flywheel", "Line 2", "Heat Treatment", "HT-02", "L2-2382", "DEF-DIM", "MEASUREMENT", "2026-07-07", "IN_PROGRESS")),
    ("HC-34", "decoy", False,
     ("Tool change interval undefined", "No tracking of insert usage.", "Steering Knuckle", "Line 1", "CNC Turning", "CT-01", "L1-2384", "DEF-FINISH", "TOOL_LIFE", "2026-08-10", "CLOSED"),
     ("Label printed in wrong language", "Traveller label shows foreign language text.", "Steering Knuckle", "Line 1", "CNC Turning", "CT-01", "L1-2384", "DEF-DAMAGE", "METHOD", "2026-08-11", "IN_PROGRESS")),
    ("HC-35", "decoy", False,
     ("Quench delay observed", "Quench started late after furnace door opened.", "Axle Shaft", "Line 5", "Heat Treatment", "HT-05", "L5-2386", "DEF-HARD", "HEAT_TREAT", "2026-09-21", "CLOSED"),
     ("Lubricant leak under conveyor", "Drip tray full beneath belt drive.", "Axle Shaft", "Line 5", "Heat Treatment", "HT-05", "L5-2386", "DEF-DAMAGE", "MAINTENANCE", "2026-09-22", "IN_PROGRESS")),
    ("HC-36", "decoy", False,
     ("Missing torque stripe on bolts", "No paint stripe after final tightening.", "Wheel Hub", "Line 3", "Assembly", "AS-03", "L3-2388", "DEF-DAMAGE", "METHOD", "2026-05-04", "CLOSED"),
     ("Packing carton damaged in transit", "Carton corners crushed on pallet before shipping.", "Wheel Hub", "Line 3", "Assembly", "AS-03", "L3-2388", "DEF-DAMAGE", "ENVIRONMENT", "2026-05-05", "IN_PROGRESS")),
    ("HC-37", "decoy", False,
     ("Runout high on shaft", "Runout above limit at second journal.", "Axle Shaft", "Line 1", "Grinding", "GR-01", "L1-2390", "DEF-RUNOUT", "FIXTURE", "2026-06-08", "CLOSED"),
     ("Gauge master chipped", "Master pin chipped at tip.", "Axle Shaft", "Line 1", "Grinding", "GR-01", "L1-2390", "DEF-DIM", "MEASUREMENT", "2026-06-09", "IN_PROGRESS")),
    ("HC-38", "decoy", False,
     ("Porosity found on section", "Porosity near boss on cut section.", "Steering Knuckle", "Line 4", "Casting", "CA-04", "L4-2392", "DEF-POROS", "MATERIAL", "2026-07-13", "CLOSED"),
     ("Documentation signature missing", "Operator signature absent on traveller sheet.", "Steering Knuckle", "Line 4", "Casting", "CA-04", "L4-2392", "DEF-DAMAGE", "OPERATOR", "2026-07-14", "IN_PROGRESS")),
    ("HC-39", "decoy", False,
     ("Colour mismatch against master", "Gloss and colour differ from approved panel.", "Flywheel", "Line 4", "Surface Coating", "SC-04", "L4-2394", "DEF-COAT", "MATERIAL", "2026-08-17", "CLOSED"),
     ("Oven temperature log incomplete", "Cure oven log shows gaps over two shifts.", "Flywheel", "Line 4", "Surface Coating", "SC-04", "L4-2394", "DEF-COAT", "METHOD", "2026-08-18", "IN_PROGRESS")),
    ("HC-40", "decoy", False,
     ("Scratch on journal", "Scratch spiral on journal surface.", "Brake Disc", "Line 3", "Grinding", "GR-03", "L3-2396", "DEF-FINISH", "TOOL_LIFE", "2026-09-28", "CLOSED"),
     ("First aid box empty", "Box lacks plasters and eye wash refill.", "Brake Disc", "Line 3", "Grinding", "GR-03", "L3-2396", "DEF-DAMAGE", "OPERATOR", "2026-09-29", "IN_PROGRESS")),
]


def content_words(title: str, description: str) -> set[str]:
    """Words left after removing generic vocabulary (crude plural stemming)."""
    out: set[str] = set()
    for w in re.findall(r"[a-z]+", f"{title} {description}".lower()):
        if len(w) < 3:
            continue
        s = w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
        if w in GENERIC_WORDS or s in GENERIC_WORDS:
            continue
        out.add(s)
    return out


def _make_nc(nc_id: str, rec: tuple):
    from app.contracts import NC, AuditType, NCStatus, Severity
    from app.engine import taxonomy as tx

    title, desc, product, line, process, machine, lot, defect, rc, raised, status = rec
    raised_at = datetime.fromisoformat(raised).replace(hour=10)
    return NC(
        id=nc_id, audit_type=AuditType.product, title=title, description=desc,
        severity=Severity.major, product=product, process=process, line=line,
        department_id=tx.PROCESS_DEPARTMENT[process], machine=machine, lot=lot,
        defect_code=defect, root_cause_category=rc, status=NCStatus(status),
        auditee_id=201, auditor_id=101, raised_at=raised_at,
        target_date=(raised_at + timedelta(days=30)).date(),
        closed_at=raised_at + timedelta(days=12) if status == "CLOSED" else None,
    )


def load_hard_cases() -> list[dict[str, Any]]:
    cases = []
    for pid, needs, label, a, b in PAIRS:
        cases.append({
            "id": pid, "needs": needs, "label": label,
            "a": _make_nc(f"{pid}-A", a), "b": _make_nc(f"{pid}-B", b),
        })
    return cases