# Member 3 — test management: progress, risks, traceability, exit criteria

Author: Member 3 · Reporting date: Mon 23 Nov 2026 (submission Sat 28 Nov 2026) · Plan: `Documents/Member3-Plan.md`.

## 1. Weekly progress report — week of 23 Nov 2026

| Work package | Planned (PERT E, h) | Status 23 Nov | Evidence |
|---|---|---|---|
| WP1 Environment, tools, fixtures | 4.3 | Done | 34-order reset/verify; tool versions in `tool-versions.md` |
| WP2 UC-05/06 specifications | 3.2 | Done | `sqe/use-cases/UC-05.md`, `UC-06.md` |
| WP3 UC-05/06 automation | 8.5 | Done | 14 tests: 11 pass, 3 expected failures (D-01..D-03) |
| WP4 Usability task tests | 3.2 | Done | USA-01, USA-02 (keyboard focus order, error explains correction) |
| WP5 Lighthouse + axe, fix, rerun | 7.3 | Done | S3: Lighthouse a11y 78 → 100, axe 0; 59 → 7 issues |
| WP6 Security | 8.5 | Done | 13/13 access decisions; ZAP 2,419 messages; 5 controls; audit |
| WP7 Performance | 5.3 | Done | 4 k6 runs, all within limits |
| WP8 Recovery | 5.3 | Done | 4 pass + 1 strict xfail (D-04); sensitivity probe |
| WP9 Issues, RCA, report sections | 5.2 | In progress | `defects-and-rca.md`; GitHub issues drafted, not yet filed |
| WP10 Viva preparation | 3.2 | Not started | rehearsal checklist in the plan §14 |

**Deviations and control actions taken**

| Deviation | Impact | Control action |
|---|---|---|
| `winget` unavailable; slow network (~150 KB/s) | Tool setup took ~45 min of waiting | Portable k6/JRE/ZAP downloads in parallel with writing tests |
| First UC-05 E1 design used an invalid date the browser never sends (date picker replaces it) | Test asserted the wrong thing | Probed the field, redesigned E1/E1b/E1c, recorded finding U-01 |
| Race condition: API read-back ran before the keyboard submit was processed, so a defect was masked once | False pass | All submits now wait for the POST response (`submitAndWait`); suite re-run on fresh fixtures |
| Lighthouse audited the login page (session pinned to User-Agent) | Invalid baseline | Redirect guard caught it; `emulatedUserAgent: false`; documented as security control C5 |
| Playwright HTML report contained test passwords | Credential leak in evidence | `sqe/m3_sanitize_report.py` + independent re-scan (0 secrets) before every commit |
| My UC-05/06 draft overlapped UC-01/02/03 | Double counting | Redefined flows (plan §4.1); to be confirmed with the team |
| Teammates not yet informed of shared-file changes | Merge conflicts later | All shared-file changes are additive; list in §6 to send |

**Actual versus estimated effort.** The automation and documents in this report were produced in an AI-assisted session (disclosed in `sqe/ai-use.md`) between 21:00 and 23:10 on 23 Nov; most of the first 45 minutes was waiting for downloads. The wall-clock time is therefore far below the 54 h PERT estimate, which assumed unassisted work. It is **not** a fair measure of the student effort the estimate describes: the remaining effort is Member 3's own review of every test and report, re-running each suite, and viva preparation. Record those hours here at the next weekly review:

| Activity (Member 3's own) | Estimate (h) | Actual (h) |
|---|---|---|
| Review and understand every Member 3 test and report | 8 | |
| Re-run each suite personally and compare with the evidence | 3 | |
| File GitHub issues, agree flow changes with the team | 2 | |
| Viva rehearsal (owned areas + live task) | 3.2 | |

## 2. GQM metrics (Member 3 scope)

| Goal | Question | Metric | Value | Reading in context |
|---|---|---|---|---|
| Assess product quality of W1/W2 | How many defects per size? | Defect density = confirmed defects in the five scoped Orders files ÷ KLOC | **4 ÷ 11.382 KLOC = 0.35 defects/KLOC** (D-01..D-04; D-05 is outside the scoped files; 11,382 NCLOC from the team's SonarQube scan) | Low density for a mature product, but 3 of the 4 are Major and all sit in the two workflows' validation and transaction code. |
| Control test progress | How many requirements have executed checks? | Requirements coverage = requirements with an executed Member 3 check ÷ 9 | **7 ÷ 9 = 78 %** (PAY-01, PAY-04, CAN-01..05) | PAY-02 (expired order) and PAY-03 (repeat payment) are covered by Tawassul's/Member 2's suites, not mine. |
| Control defect handling | Are fixes holding? | Reopen rate = reopened ÷ resolved | **n/a (0 ÷ 0)** | No defect has been resolved yet; measure after fixes land. |

## 3. Risk register — Member 3 additions and updates (likelihood × impact, 1–5)

| ID | Type | Risk | L | I | Score | Technique / depth | Outcome 23 Nov |
|---|---|---|---|---|---|---|---|
| R4 | Product | Viewer can perform a write | 4 | 5 | 20 | 12 direct access decisions over UI and API, state read-back | **Not realised**: 0 unauthorized writes. Lower likelihood to 2 (score 10). |
| R1 | Product | Duplicate payment or fee on retry | 4 | 5 | 20 | UC-05 alt 1 reuse, REC-01/02 replay | **Not realised** in tested paths (0 duplicates). |
| R2 / R6 | Product | Status without matching records / partial data on failure | 4 / 3 | 5 | 20 / 15 | REC-01b atomic rollback, REC-02 | **Realised for W1 → D-04.** Cancellation is atomic; payment confirmation is not. Keep at 20. |
| R5 | Product | Excess fee or wrong retained total | 4 | 4 | 16 | BVA 19.99/20.01, UC-06 exc 1 | Upper bound holds; see R15. |
| R11 | Project | Chromium bypasses proxy for loopback → empty ZAP scan | 4 | 3 | 12 | `<-loopback>` bypass rule; message count checked (121 → 2,419) | Mitigated. Close. |
| R12 | Project | Fixture collisions between members | 3 | 4 | 12 | M3-prefixed orders; reset before each suite | Mitigated so far. |
| R13 | Project | Perf numbers not representative | 4 | 3 | 12 | DEBUG off, fixed conditions, caveat | Mitigated / accepted (stated in report). |
| R14 | Project | Lighthouse variance hides before/after change | 3 | 2 | 6 | 3 runs, median | Not realised (runs identical). Close. |
| R15 | Product | Negative fee or payment accepted | 3 | 5 | 15 | BVA below 0 at UI level | **Realised → D-01, D-02.** Raise likelihood to 5 (score 25): any manager typo triggers it. |
| R16 | Product | Partial state when payment confirmation fails part-way | 2 | 5 | 10 | REC-02 | **Realised → D-04.** |
| R17 | Product | Keyboard / assistive-technology users blocked | 3 | 4 | 12 | USA-02, axe, Lighthouse, layout fix | Reduced: S2/S3 now 0 violations; S1 has 7 open issues. Score 6. |
| R18 | Product | Cookie/header protections depend on the deployment (http, no proxy) | 2 | 4 | 8 | C1, C4 review | Confirmed environment-dependent; deployment requirement documented. |
| R19 | Product | Outdated vendored client libraries / weak CSP | 2 | 3 | 6 | ZAP passive | SEC-F1, SEC-F2 recorded. |
| R20 | Product | Vulnerable Python dependency | 2 | 3 | 6 | pip-audit | SEC-F4 (oauthlib) recorded; not reachable from W1/W2. |
| R21 | Product | Security monitoring degraded by false alarms | 3 | 2 | 6 | Server log review | **Realised → D-05.** |

## 4. Traceability — Member 3 checks

| Requirement / rule | Member 3 checks (level) | Result |
|---|---|---|
| PAY-01 pending order paid for outstanding amount (BR-01) | UC-05 main / USA-01 (E2E), REC-02c (integration) | Pass |
| PAY-04 viewer cannot mark paid | AC-04, AC-05 (UI), AC-09 (API) | Pass |
| CAN-01 paid order canceled without fee (BR-02, BR-04) | UC-06 main (E2E), AC-02 | Pass |
| CAN-02 retained fee within total (BR-03, BR-04) | UC-06 exc 1 correction step (E2E), REC-01/01b (integration) | Pass |
| CAN-03 fee above total rejected, state consistent (BR-03) | UC-06 exc 1 rejection step (E2E) | Pass |
| CAN-03 lower bound (fee ≥ 0, BR-03) | UC-06 exc 2 (E2E) | **Fail → D-01** |
| CAN-04 no duplicate fee on replay | REC-01/01b replay step (integration) | Pass |
| CAN-05 viewer cannot cancel | AC-06, AC-07 (UI), AC-10 (API) | Pass |
| BR-01 amount validity (> 0) | UC-05 probe H2 | **Fail → D-02** |
| W1 consistency after failure | REC-02, REC-02b | **Fail → D-04** |
| Usability: errors explain the correction | USA-02 (pass), UC-05 exc 1c | **Fail → D-03** |
| Accessibility of key screens | A11Y S1–S3 axe + Lighthouse | S2, S3 pass after fix; S1 7 open |

## 5. Exit criteria — actual versus target (Member 3 areas)

| # | Criterion | Target | Actual | Met? | Tied to risk |
|---|---|---|---|---|---|
| E1 | Unauthorized writes in access checks | 0 | **0** (13/13 decisions correct) | ✔ | R4 (20) |
| E2 | Duplicate business records after failure, retry, replay | 0 | **0** | ✔ | R1 (20), R6 (15) |
| E3 | Negative or above-cap fee persisted | 0 | above-cap 0, **negative 1 (D-01)** | ✘ | R15, R5 |
| E4 | UC-05/06 flows automated and executed | 10/10 | **10/10** (+4 extra probes/known-defect checks) | ✔ | — |
| E5 | Serious/critical axe violations on the fixed screen; LH ≥ baseline | 0; ≥ 78 | **0; 100** | ✔ | R17 |
| E6 | k6 limits at 1 and 5 VUs | all 4 runs | **4/4** within limits | ✔ | R8 |
| E7 | High/critical dependency advisories without triage | 0 | **0** (none high/critical; all triaged) | ✔ | R20 |

**Member 3 recommendation: HOLD** until D-01 and D-02 are fixed and their tests pass (E3, highest-scoring realised risk R15), with D-04 either fixed or covered by the documented recovery runbook. All other Member 3 criteria are met.

## 6. Items to send to the team (not yet sent — Member 3 is working alone this week)

1. UC-05/UC-06 flows were redefined to avoid double counting with UC-01/02/03 (plan §4.1).
2. `sqe/orders_fixtures.py` now has 20 additional `M3*` orders and rewrites the alias map in `fixtures.json` when it changes; `sqe/windows.ps1` gained `recovery` and `serve-perf`.
3. `src/pretix/control/templates/pretixcontrol/base.html` and two SCSS files were changed by the accessibility fix — UC-01/02 were re-run and still pass.
4. For Member 2 (API): D-01's API path (`cancellation_fee` without minimum), the hypothesis that API `mark_paid` after D-04 creates a 0.00 payment, and H3 (API quota rejection leaves a confirmed payment) — all still to be executed at API level.
5. For Tawassul (CI): add `sqe\windows.ps1 recovery`, `access.spec.js` and `uc05-uc06.spec.js` to the pipeline; D-03 and the accessibility fix are candidates for the "documented fix" PR.
6. Risk IDs R11–R21 and the realised-risk updates in §3 to merge into the team register.
