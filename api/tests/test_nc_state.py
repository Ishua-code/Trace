import pytest
from fastapi import HTTPException
from app.services.nc_state import check_transition, next_states


def test_happy_path_legal():
    check_transition("OPEN", "ASSIGNED", "auditing_head")
    check_transition("EVIDENCE_SUBMITTED", "AUDITOR_VERIFIED", "auditor")


def test_illegal_move_is_409():
    with pytest.raises(HTTPException) as e:
        check_transition("OPEN", "CLOSED", "admin")
    assert e.value.status_code == 409


def test_wrong_role_is_403():
    with pytest.raises(HTTPException) as e:
        check_transition("EVIDENCE_SUBMITTED", "AUDITOR_VERIFIED", "auditee")
    assert e.value.status_code == 403


def test_next_states():
    assert set(next_states("EVIDENCE_SUBMITTED")) == {"AUDITOR_VERIFIED", "REJECTED"}