# AI-use record

| Tool | Purpose | Output | Verification performed |
| --- | --- | --- | --- |
| OpenAI Codex | Consolidate overlapping assignment instructions | Nine phase guides and a two-teammate commit checklist | Checked the original PDF checksum, case ownership and local links. |
| OpenAI Codex | Begin work owned by Tawassul before teammate contributions, on native Windows, with verification as each phase progresses | Windows app and fixture harness, test basis, white-box tests, Chromium cases and initial CI checks | Ran Django checks, two verified resets, the same-order journey, restart readback, 30 unit cases, two targeted mutations, SonarQube with coverage and 10 Chromium flows. The handoff records actual results and gaps. |

The work request and verification instructions are retained in the project conversation. Tawassul should record the tests rerun and edits made during individual review before submitting the final package.

## Member 3 (Zubair) — 23 Nov 2026

Tool: Claude Code (model Claude Opus 5.5), run locally in the repository on branch `zubair/develop` and `zubair/feature/*`. Every commit it made carries a `Co-Authored-By: Claude` trailer. The full conversation (prompts and outputs) is kept by Member 3.

| Tool | Purpose | Output | Verification performed (by the tool, during the session) |
| --- | --- | --- | --- |
| Claude Code | Read the assignment PDF and the existing team work; review Tawassul's plan against the rubric | Gap analysis (CI/mutation, coverage, CFG comparison, defect count, integrity risk) | Opened the PDF and every referenced repo file; cited file:line for each claim. |
| Claude Code | Plan Member 3's areas | `Documents/Member3-Plan.md` (facts F1–F13, hypotheses H1–H5, flows, risks, estimates) | Every source fact was checked in the pinned code; hypotheses were marked unverified until tested. |
| Claude Code | Environment and fixtures | venv, Playwright/axe/Lighthouse install, portable k6/ZAP/JRE; 20 `M3*` fixture orders; runner actions | `check`, `reset`, `verify` run: 34/34 orders matched the contract. |
| Claude Code | UC-05/UC-06 specs and Playwright tests, usability tests | `sqe/use-cases/UC-05.md`, `UC-06.md`, `uc05-uc06.spec.js`, `keyboard.js`, `rules.js` | Ran on fresh fixtures (11 pass, 3 expected failures). Found and fixed its own errors: an invalid-date test the browser never submits (probed the field), and a read-back race that masked a defect once. Confirmed each defect by reading the stored order through the API. |
| Claude Code | Access matrix, ZAP passive scan, control review, dependency audit | `access.spec.js`, `security-assessment.md`, ZAP/audit evidence | 13/13 decisions; 403 cause checked by response page title; ZAP message count verified > 0; every alert type triaged against source; evidence scanned for secrets. |
| Claude Code | Accessibility baseline, layout fix, re-test | `a11y.spec.js`, `tools/lighthouse.mjs`, `tools/merge-a11y.mjs`, `base.html`/SCSS fix, `a11y-findings.md` | Caught Lighthouse auditing the login page (redirect guard) and fixed it; corrected its own merge keying and wrong per-screen counts against the raw data; regression suite re-run (38 tests). |
| Claude Code | k6 workload and recovery tests | `order-read.k6.js`, `test_recovery.py`, `performance-recovery.md`, `m3_perf_summary.py` | Limits fixed before measuring; DEBUG-off confirmed; p95 recomputed from raw data matches k6; sensitivity probe showed REC-01b detects missing atomicity and REC-01 does not (wording corrected). Corrected a wrong request total (1,021 → 846) in its own report. |
| Claude Code | Defect log, RCA, Pareto, test management | `defects-and-rca.md`, `test-management.md`, `README.md` | Source line references re-checked; code-reading-only claims labelled as such. |

**Still to be done by Member 3 personally before submission:** read and understand every file above, re-run each suite and compare with the committed evidence, file the GitHub issues, record own effort in `sqe/member3/test-management.md` §1, and note here any changes made after review.
