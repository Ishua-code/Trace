BASE PROMPT (paste at the start of every member's AI coding session and save as `CLAUDE.md` in the repo root)

```
You are helping build TRACE, our entry for Sakthi Hackathon 2.0, Round 2, problem statement PS-015
("Digital Product Audit and Revalidation Audit Management Dashboard"). We were selected on our Round 1
idea. We now need a working, deployed prototype, a 5-minute demo video and a <=10 slide PPT by 23 Nov.
We want to WIN, so it must work end to end, look exceptional and be technically honest.

PRODUCT
TRACE digitizes the full audit lifecycle (monthly plan upload -> daily auditor schedule -> digital
checklist/report -> NC raised and auto-assigned -> action plan/owner/target date -> evidence ->
auditor verification -> Auditing Head final approval -> reminders/escalation -> searchable history and
exports) AND adds the TRACE Failure Propagation & Closure Assurance Engine:
 1. Cross-Audit Failure Mapping: explainable graph linking NCs by product, process, department,
    root-cause category, machine/lot and text similarity.
 2. Quality Escape Simulator: before closure, evaluate the fix against the original NC, related past
    failures and unresolved connected NCs; produce an evidence-cited report with verdict
    CLEAR / VERIFY / HOLD. Rule-based and explainable, NOT a prediction guarantee.
 3. Targeted verification tasks and risk-adaptive audit planning (mandatory audits stay protected).
The Auditing Head always makes the final, logged decision. The Closure Gate is the heart of the demo.

NON-NEGOTIABLE RULES
- Python is the primary language: FastAPI backend, engine, seed, eval, workers, exports, tests.
  Frontend is Next.js + TypeScript + Tailwind + shadcn/ui. NO Streamlit/Gradio/Dash.
- Must deploy on Vercel (web/ and api/ as two projects from one monorepo). Keep serverless limits in
  mind: no heavy ML libs at runtime (no torch / sklearn / sentence-transformers), light imports,
  upload files directly to Blob/Storage (never through the API), cron limits on Hobby plan.
- Honesty: every number shown in UI/PPT must be computed by code. No hardcoded KPIs, no fake results.
  Synthetic data must be labelled synthetic. Never tune on the test split.
- Every git commit message MUST start with "feat", format: feat(scope): message. This includes fixes,
  tests and docs. Branch names: feat/<yourname>-<topic>. Open a PR to main; CI must be green.
- Contracts are frozen: api/app/contracts.py (Pydantic types) and the DB schema. Do not change them
  without telling Ishwarya (and Hanu for engine types). Code against the contract, use mocks until the
  real endpoint lands.
- Demo-first: if a feature will not appear in the video or the traceability table, do not build it.
- Quality bar: typed code, ruff-clean Python, pytest for logic, loading/empty/error states in the UI,
  accessible (keyboard + contrast), responsive down to 375px, pages usable in <2 s.
- No secrets in git. Use .env.example. Never print tokens.

GOLDEN SCENARIO (must always work; see docs/scenario.md)
NC-0412 (Line 2 brake drum bore burr) looks resolved after a deburring tool replacement. TRACE links it
to unresolved NC-0377 (Line 4, "sharp edge", no tool-life tracking) and closed-but-recurred NC-0390
(heat treatment, tool change interval undefined). Verdict HOLD, evidence per link, three verification
tasks, Auditing Head records a decision, event is hash-chained in the audit log.

TEAM
Ishwarya: tech lead + workflow backend. Hanu: TRACE engine + evaluation. Harish: UI lead (management +
TRACE experience). Shamini: auditor/auditee experience, QA, storytelling. Stay in your lane; if you
need something from another lane, open a GitHub issue tagged with their name and mock it meanwhile.

WORKING STYLE
Before coding: read CLAUDE.md, docs/architecture.md, docs/scenario.md and contracts.py. Plan briefly,
build the smallest vertical slice, run tests, commit small, open a PR with a screenshot or test output.
At the end of each session, summarize what shipped, what is blocked and the next step.
```
GIT FLOW
- Always branch from develop: feat/<yourname>-<topic>.
- Open PRs into develop only. Never push or open a PR directly to main.
- Only the tech lead (Ishwarya) merges develop into main, once, when the build is final and tested.
- Before starting new work: git checkout develop; git pull

---