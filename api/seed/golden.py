"""Golden scenario records (SYNTHETIC demo data). DRAFT: reconcile with docs/scenario.md.

Imports contracts lazily so this module stays importable without the api path set.
User ids below are PLACEHOLDERS; Ishwarya's user seed must use the same ids.
"""
from __future__ import annotations

from datetime import date, datetime

AS_OF = datetime(2026, 11, 12, 9, 0)  # demo "today" for overdue logic

# Placeholder user ids (ASSUMPTION - align with the users seed)
AUDITOR_ID = 101
AUDITEE_L2 = 201   # Machining, Line 2
AUDITEE_L4 = 202   # Machining, Line 4
AUDITEE_HT = 203   # Heat Treatment
HEAD_ID = 301

# Action scope per NC (the contract has no scope field yet; used by rule R2 until A6 lands)
ACTION_SCOPE_LINES: dict[str, list[str]] = {
    "NC-0412": ["Line 2"],
    "NC-0377": ["Line 4"],
    "NC-0390": ["Line 3"],
}

EXPECTED = {
    "focus_nc": "NC-0412",
    "verdict": "HOLD",
    "linked_ncs": {"NC-0377", "NC-0390"},
    "must_not_link": {"NC-0401", "NC-0408"},  # decoys
    "task_count": 3,
    "task_keywords": ["tool-life", "30 pcs", "CP-07"],
}


def build_golden():
    from app.contracts import (
        NC,
        ActionPlan,
        AuditType,
        Evidence,
        NCStatus,
        Severity,
        Verification,
    )

    ncs = [
        NC(
            id="NC-0377", audit_type=AuditType.product,
            title="Sharp edge on drum bore, Line 4",
            description="Sharp edge found on machined bore surface of brake drum at Line 4. "
                        "No tool-life tracking in place for the finishing insert.",
            severity=Severity.major, product="Brake Drum", process="Bore Machining",
            line="Line 4", department_id=2, machine="BM-04", lot="L4-2209",
            defect_code="DEF-BURR", root_cause_category="TOOL_LIFE",
            status=NCStatus.IN_PROGRESS, auditee_id=AUDITEE_L4, auditor_id=AUDITOR_ID,
            raised_at=datetime(2026, 6, 2, 10, 0), target_date=date(2026, 7, 2),
        ),
        NC(
            id="NC-0390", audit_type=AuditType.revalidation,
            title="Edge defect recurrence after heat treatment tooling change",
            description="Tool change interval undefined for heat treatment fixture tooling; "
                        "edge defect returned on drums after earlier fix.",
            severity=Severity.major, product="Brake Drum", process="Heat Treatment",
            line="Line 3", department_id=3, machine="HT-01", lot="L3-2231",
            defect_code="DEF-BURR", root_cause_category="TOOL_LIFE",
            status=NCStatus.CLOSED, auditee_id=AUDITEE_HT, auditor_id=AUDITOR_ID,
            raised_at=datetime(2026, 6, 20, 11, 0), target_date=date(2026, 7, 25),
            closed_at=datetime(2026, 8, 10, 15, 0),
        ),
        NC(
            id="NC-0412", audit_type=AuditType.product,
            title="Burr on brake drum bore, Line 2",
            description="Burr observed on brake drum bore after machining at Line 2. "
                        "Deburring tool replaced.",
            severity=Severity.major, product="Brake Drum", process="Bore Machining",
            line="Line 2", department_id=2, machine="BM-02", lot="L2-2307",
            defect_code="DEF-BURR", root_cause_category="TOOL_LIFE",
            status=NCStatus.AUDITOR_VERIFIED, auditee_id=AUDITEE_L2, auditor_id=AUDITOR_ID,
            raised_at=datetime(2026, 11, 3, 9, 30), target_date=date(2026, 11, 17),
        ),
        # ---- decoys (ADDITIONAL): look related, must NOT link
        NC(
            id="NC-0401", audit_type=AuditType.product,
            title="Coating peel on wheel hub, Line 5",
            description="Paint flaking on wheel hub flange, poor adhesion at Line 5.",
            severity=Severity.minor, product="Wheel Hub", process="Surface Coating",
            line="Line 5", department_id=4, machine="SC-01", lot="L5-2290",
            defect_code="DEF-COAT", root_cause_category="MATERIAL",
            status=NCStatus.CLOSED, auditee_id=AUDITEE_HT, auditor_id=AUDITOR_ID,
            raised_at=datetime(2026, 10, 8, 10, 0), target_date=date(2026, 10, 22),
            closed_at=datetime(2026, 10, 20, 14, 0),
        ),
        NC(
            id="NC-0408", audit_type=AuditType.product,
            title="Bore gauge overdue for calibration, Line 2",
            description="Bore gauge used at Line 2 brake drum inspection past calibration date.",
            severity=Severity.minor, product="Brake Drum", process="Final Inspection",
            line="Line 2", department_id=6, machine="GA-02", lot="L2-2307",
            defect_code="DEF-DIM", root_cause_category="MEASUREMENT",
            status=NCStatus.CLOSED, auditee_id=AUDITEE_L2, auditor_id=AUDITOR_ID,
            raised_at=datetime(2026, 10, 15, 10, 0), target_date=date(2026, 10, 29),
            closed_at=datetime(2026, 10, 27, 16, 0),
        ),
    ]

    actions = [
        ActionPlan(
            id=1, nc_id="NC-0377", root_cause_category="TOOL_LIFE",
            corrective_action="Replace finishing insert and deburr affected drums at Line 4.",
            owner_id=AUDITEE_L4, target_date=date(2026, 7, 2),
            created_at=datetime(2026, 6, 4, 9, 0),
        ),
        ActionPlan(
            id=2, nc_id="NC-0390", root_cause_category="TOOL_LIFE",
            corrective_action="Replace worn fixture tooling and rework affected lot.",
            owner_id=AUDITEE_HT, target_date=date(2026, 7, 25),
            created_at=datetime(2026, 6, 22, 9, 0),
        ),
        ActionPlan(
            id=3, nc_id="NC-0412", root_cause_category="TOOL_LIFE",
            corrective_action="Replace the deburring tool at Line 2.",
            owner_id=AUDITEE_L2, target_date=date(2026, 11, 17),
            created_at=datetime(2026, 11, 4, 9, 0),
        ),
    ]

    evidence = [
        Evidence(  # weak: single photo, no before/after (feeds rule R5)
            id=1, nc_id="NC-0412", file_url="https://example.invalid/ev/nc0412-tool.jpg",
            file_name="nc0412-tool.jpg", uploaded_by=AUDITEE_L2,
            uploaded_at=datetime(2026, 11, 8, 14, 0), has_before_after=False,
        ),
        Evidence(
            id=2, nc_id="NC-0390", file_url="https://example.invalid/ev/nc0390-fixture.jpg",
            file_name="nc0390-fixture.jpg", uploaded_by=AUDITEE_HT,
            uploaded_at=datetime(2026, 8, 5, 10, 0), has_before_after=True,
        ),
    ]

    verifications = [
        Verification(
            id=1, nc_id="NC-0412", auditor_id=AUDITOR_ID, accepted=True,
            comment="New deburring tool fitted; sample parts clean.",
            verified_at=datetime(2026, 11, 10, 11, 0),
        ),
        Verification(
            id=2, nc_id="NC-0390", auditor_id=AUDITOR_ID, accepted=True,
            comment="Fixture tooling replaced.", verified_at=datetime(2026, 8, 8, 11, 0),
        ),
    ]

    return {
        "ncs": ncs, "action_plans": actions, "evidence": evidence,
        "verifications": verifications, "scope_lines": ACTION_SCOPE_LINES,
        "expected": EXPECTED, "as_of": AS_OF,
    }