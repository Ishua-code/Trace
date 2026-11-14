# TRACE – Quality Assurance Test Plan

## 1. Document Information

| Field | Details |
|---|---|
| Project | TRACE – Digital Product Audit and Revalidation Audit Management Dashboard |
| Document | QA Test Plan |
| Prepared by | Shamini |
| Date | 14 November 2026 |
| Version | 1.0 |
| Status | Test plan prepared; execution pending |

## 2. Objective

The objective of this test plan is to verify that TRACE supports the complete
audit lifecycle, enforces role-based access, identifies recurring quality
failures and maintains a reliable audit history.

Tests will cover functional behaviour, validation, permissions, error handling
and the TRACE Failure Propagation and Closure Assurance Engine.

## 3. Testing Scope

### In scope

- User authentication and role-based access.
- Audit plan upload and schedule management.
- Digital checklist completion and report submission.
- Non-conformance (NC) creation and assignment.
- Corrective action plan submission.
- Evidence upload and auditor verification.
- Closure Gate verdict and verification tasks.
- Auditing Head approval.
- Notifications and overdue escalation.
- Event history and hash-chain verification.
- Search, reporting and export functionality.

### Out of scope

- Testing with real confidential company or customer data.
- Production security certification.
- Performance claims without measured test results.

## 4. Test Environment

| Component | Environment |
|---|---|
| Operating System | Windows |
| Backend | Python / FastAPI |
| Frontend | Next.js / TypeScript |
| Database | Supabase PostgreSQL |
| Browser | Google Chrome |
| Test Framework | Pytest and Playwright |
| Test Data | Synthetic demo data |

## 5. Test Execution Status

Use these statuses when executing tests:

- NOT RUN – Test has not been executed.
- PASS – Actual result matches expected result.
- FAIL – Actual result does not match expected result.
- BLOCKED – Feature or dependency is not available.
- RETEST – Failed test has been fixed and needs testing again.

All test cases below start as NOT RUN. Do not mark a test as PASS without
actually executing it.

## 6. Functional Test Cases

### TC-001: User Login

**Priority:** High

**Precondition:** A valid demo user account exists.

**Steps:**
1. Open the TRACE application.
2. Navigate to the login page.
3. Enter valid login credentials.
4. Submit the login form.

**Expected Result:**
- User should be authenticated successfully.
- The application should display the appropriate user dashboard.
- The user's role should be available to the application.

**Status:** NOT RUN

### TC-002: Invalid Login

**Priority:** High

**Precondition:** Login page is accessible.

**Steps:**
1. Open the login page.
2. Enter invalid credentials.
3. Submit the form.

**Expected Result:**
- Login should be rejected.
- An appropriate error message should be displayed.
- Protected application data should not be accessible.

**Status:** NOT RUN

### TC-003: Audit Plan Upload

**Priority:** High

**Precondition:** User has permission to upload an audit plan.

**Steps:**
1. Open the audit plan upload page.
2. Upload a valid sample audit plan.
3. Review the validation result.

**Expected Result:**
- Valid records should be accepted.
- Invalid records should show understandable validation errors.
- The user should be able to identify which records need correction.

**Status:** NOT RUN – Awaiting feature availability.

### TC-004: Auditor Daily Schedule

**Priority:** High

**Precondition:** An audit plan and auditor schedule exist.

**Steps:**
1. Log in as an Auditor.
2. Open the daily schedule.
3. Select an assigned audit.

**Expected Result:**
- The auditor should see their assigned audits.
- Audit details should be displayed correctly.
- Unauthorized audits should not be accessible.

**Status:** NOT RUN – Awaiting feature availability.

### TC-005: Digital Checklist Submission

**Priority:** High

**Precondition:** An audit is assigned to the logged-in Auditor.

**Steps:**
1. Open an assigned audit.
2. Complete checklist items using Pass, Fail or N/A.
3. Add remarks where required.
4. Save the draft.
5. Submit the completed checklist.

**Expected Result:**
- Checklist responses should be saved correctly.
- Required validation should be enforced.
- The submitted report should be associated with the correct audit.

**Status:** NOT RUN – Awaiting feature availability.

### TC-006: Non-Conformance Creation

**Priority:** High

**Precondition:** An audit checklist contains a failed item.

**Steps:**
1. Open the failed checklist item.
2. Select the option to raise an NC.
3. Enter severity, product, process, machine and lot details.
4. Submit the NC.

**Expected Result:**
- A new NC should be created.
- The NC should contain the correct failure details.
- The NC should be available for corrective action.

**Status:** NOT RUN – Workflow integration pending.

### TC-007: Corrective Action Plan Submission

**Priority:** High

**Precondition:** An NC is assigned to an Auditee.

**Steps:**
1. Log in as the assigned Auditee.
2. Open the My Actions section.
3. Select the assigned NC.
4. Enter the root cause, corrective action, owner and target date.
5. Submit the action plan.

**Expected Result:**
- The action plan should be saved.
- Required fields should be validated.
- The assigned NC should display the updated action status.

**Status:** NOT RUN – Awaiting feature availability.

### TC-008: Evidence Upload and Verification

**Priority:** High

**Precondition:** A corrective action plan exists.

**Steps:**
1. Log in as the Auditee.
2. Open the assigned NC.
3. Upload supporting evidence.
4. Log in as the Auditor.
5. Review the uploaded evidence.
6. Accept or reject the evidence with a comment.

**Expected Result:**
- Evidence should be associated with the correct NC.
- The Auditor should be able to review the evidence.
- Rejected evidence should include a reason.
- Verification status should be recorded.

**Status:** NOT RUN – Awaiting feature availability.

### TC-009: TRACE Closure Gate – Golden Scenario

**Priority:** Critical

**Precondition:** Golden scenario synthetic records are available.

**Test data:**
- NC-0412: Brake drum bore burr on Line 2.
- NC-0377: Sharp edge on Line 4; tool-life tracking missing.
- NC-0390: Historical edge defect; tool-change interval undefined.
- NC-0401: Coating peel – unrelated decoy.
- NC-0408: Bore gauge calibration – unrelated decoy.

**Steps:**
1. Open NC-0412.
2. Review its corrective action and uploaded evidence.
3. Run the TRACE Closure Gate.
4. Review related NCs and supporting evidence.
5. Review the generated verification tasks.

**Expected Result:**
- NC-0412 should be the primary NC.
- NC-0377 and NC-0390 should be identified as relevant related failures.
- NC-0401 and NC-0408 should not be incorrectly linked.
- The verdict should be HOLD because closure assurance is insufficient.
- Three targeted verification tasks should be generated.
- The reasons for the verdict should be explainable using evidence.

**Status:** NOT RUN – Requires integrated engine and workflow.

### TC-010: Auditing Head Final Approval

**Priority:** Critical

**Precondition:** A closure report is available for review.

**Steps:**
1. Log in as Auditing Head.
2. Open the closure report.
3. Review the verdict, evidence and verification results.
4. Record the final approval decision.

**Expected Result:**
- Only an authorized Auditing Head should make the final decision.
- The decision and comments should be recorded.
- The decision should appear in the event history.

**Status:** NOT RUN – Awaiting feature availability.

### TC-011: Overdue Action Escalation

**Priority:** High

**Precondition:** An action has passed its target date and remains unresolved.

**Steps:**
1. Open an overdue action.
2. Trigger or wait for the configured escalation process.
3. Review the notification and action status.

**Expected Result:**
- The overdue action should be identified.
- The appropriate reminder or escalation should be generated.
- The escalation should be recorded in the system.

**Status:** NOT RUN – Awaiting feature availability.

### TC-012: Role-Based Access Control

**Priority:** Critical

**Precondition:** Demo accounts for Auditor, Auditee and Auditing Head exist.

**Steps:**
1. Log in as an Auditee.
2. Attempt to access an approval action.
3. Log in as an Auditor.
4. Attempt to perform an Auditing Head-only approval.
5. Log in as Auditing Head.
6. Verify access to the final approval action.

**Expected Result:**
- Auditee must not be allowed to approve closure.
- Auditor must not be allowed to perform Auditing Head-only approval.
- Auditing Head should have the authorized approval capability.
- Unauthorized API requests must also be rejected.

**Status:** NOT RUN

### TC-013: Event History and Hash-Chain Verification

**Priority:** High

**Precondition:** Relevant audit and NC events have been recorded.

**Steps:**
1. Open the event history.
2. Review the recorded actions.
3. Run the hash-chain verification operation.

**Expected Result:**
- Recorded events should appear in the correct history.
- Event order and hash links should be verifiable.
- The verification result should identify an invalid chain if tampering is detected.

**Status:** NOT RUN

### TC-014: Search and Export

**Priority:** Medium

**Precondition:** Audit and NC records exist.

**Steps:**
1. Open the search or reporting page.
2. Search using an NC identifier.
3. Apply available filters.
4. Export the displayed report.

**Expected Result:**
- Relevant records should be returned.
- Filters should work correctly.
- Exported data should match the selected records.

**Status:** NOT RUN – Awaiting feature availability.

## 7. Negative and Validation Tests

| Test ID | Scenario | Expected Result |
|---|---|---|
| NT-001 | Upload unsupported file format | Display validation error |
| NT-002 | Submit checklist with required fields missing | Prevent invalid submission |
| NT-003 | Submit an empty action plan | Show required-field errors |
| NT-004 | Upload unsupported evidence file | Reject the file safely |
| NT-005 | Access another user's restricted action | Deny unauthorized access |
| NT-006 | Attempt invalid NC status transition | Reject invalid transition |
| NT-007 | Submit duplicate action | Prevent unintended duplicate records |
| NT-008 | Access protected endpoint without authentication | Return unauthorized response |

**Status:** NOT RUN

## 8. Existing Automated Test Inventory

The following test files were present in the repository during preparation
of this plan. Their presence does not mean all test cases have passed.

| Existing test file | Area to inspect |
|---|---|
| test_auth.py | Authentication |
| test_events.py | Event history |
| test_golden_seed.py | Golden scenario seed |
| test_hard_cases.py | Engine hard cases |
| test_engine_store.py | Engine storage |
| test_nc_state.py | NC state transitions |
| test_taxonomy.py | Taxonomy |
| test_logreg_nonneg.py | Logistic regression constraints |
| test_cv_folds.py | Cross-validation |
| test_metrics.py | Evaluation metrics |
| test_seed_generator.py | Seed generation |

## 9. Bug Reporting Format

Every failed test should be documented with:

- Bug ID
- Test Case ID
- Bug title
- Steps to reproduce
- Expected result
- Actual result
- Severity: Critical / High / Medium / Low
- Screenshot or error log
- Assigned developer
- Current status

## 10. Test Completion Criteria

Testing can be considered complete when:

1. All required functional test cases have been executed.
2. Critical role-based access tests pass.
3. The golden scenario produces the expected HOLD verdict.
4. Related failures and verification tasks are correctly generated.
5. The final approval is recorded in the event history.
6. Hash-chain verification succeeds for an untampered event history.
7. Critical and high-severity bugs are resolved or formally documented.
8. The final test results are reviewed before the demo.

## 11. Test Execution Record

| Test ID | Actual Result | Status | Evidence / Notes |
|---|---|---|---|
| TC-001 | Pending | NOT RUN | |
| TC-002 | Pending | NOT RUN | |
| TC-003 | Pending | NOT RUN | |
| TC-004 | Pending | NOT RUN | |
| TC-005 | Pending | NOT RUN | |
| TC-006 | Pending | NOT RUN | |
| TC-007 | Pending | NOT RUN | |
| TC-008 | Pending | NOT RUN | |
| TC-009 | Pending | NOT RUN | |
| TC-010 | Pending | NOT RUN | |
| TC-011 | Pending | NOT RUN | |
| TC-012 | Pending | NOT RUN | |
| TC-013 | Pending | NOT RUN | |
| TC-014 | Pending | NOT RUN | |
## Automated Test Baseline - 14 November 2026

Environment:
- Python: 3.12.10
- Pytest: 9.2.0
- Test database: SQLite in-memory
- Dependencies installed in local api/.venv

Execution:
- Tests collected: 107
- Passed: 106
- Failed: 1
- Warnings: 2

Failure:
- Test: tests/test_cv_folds.py::test_matches_existing_dev_pairs
- Error: ModuleNotFoundError: No module named 'eval.fit_weights'
- Finding: The current checkout does not contain a tracked eval/fit_weights.py.
- Status: Blocked - requires evaluation module availability or confirmation from its owner.

Warnings:
- Two JWT InsecureKeyLengthWarning messages caused by a short test secret.
- Non-blocking for this test run.

Limitations:
- SQLite in-memory execution does not verify Supabase/PostgreSQL integration.
- Functional UI test cases remain NOT RUN unless separately executed.
---
End of QA Test Plan