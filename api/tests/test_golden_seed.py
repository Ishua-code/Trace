import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, so `seed` imports

from app.engine import taxonomy as t

from seed.golden import build_golden


def test_golden_records_build_and_are_canonical():
    g = build_golden()
    ids = [n.id for n in g["ncs"]]
    assert len(ids) == len(set(ids))
    for n in g["ncs"]:
        errs = t.validate_fields(n.product, n.line, n.process, n.root_cause_category, n.defect_code)
        assert errs == [], (n.id, errs)
        assert t.PROCESS_DEPARTMENT[n.process] == n.department_id or n.process == "Final Inspection"


def test_golden_shape():
    g = build_golden()
    by_id = {n.id: n for n in g["ncs"]}
    assert by_id["NC-0412"].status.value == "AUDITOR_VERIFIED"
    assert by_id["NC-0377"].closed_at is None                      # unresolved
    assert by_id["NC-0377"].target_date < g["as_of"].date()        # overdue
    assert by_id["NC-0390"].closed_at is not None                  # closed, then recurred
    assert by_id["NC-0390"].closed_at < by_id["NC-0412"].raised_at
    cats = {by_id[i].root_cause_category for i in ("NC-0412", "NC-0377", "NC-0390")}
    assert cats == {"TOOL_LIFE"}


def test_every_nc_referenced_exists():
    g = build_golden()
    ids = {n.id for n in g["ncs"]}
    for rec in g["action_plans"] + g["evidence"] + g["verifications"]:
        assert rec.nc_id in ids
    assert g["expected"]["linked_ncs"] <= ids
    assert g["expected"]["must_not_link"] <= ids