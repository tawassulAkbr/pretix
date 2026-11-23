# Member 3 — defect log, root cause analysis and Pareto

Author: Member 3 · Date: 23 Nov 2026 · Baseline: pretix `526a79c7d` on the team fork. Every defect below was **reproduced by an automated test** whose evidence is linked; nothing is reported from reading code alone unless marked so.

## 1. Defect log (to be filed as GitHub Issues on the team fork)

Severity: impact on the business when it happens. Priority: how soon to fix, given likelihood and exposure. Lifecycle used by the team: *New → Triaged → In progress → Fixed → Verified → Closed* (or *Rejected / Deferred*).

| ID | Title | Severity | Priority | Status | Triage decision | Category | Risk | Found by / evidence |
|---|---|---|---|---|---|---|---|---|
| **D-01** | Negative cancellation fee is accepted: positions are canceled, a −0.01 fee is stored, the order total becomes −0.01 and the order stays *paid* | **Major** | **High** | New → Triaged | **Fix before release.** Breaks BR-03 and creates negative revenue records; reachable by any manager typo (e.g. "-5"). | Input validation | R15 (15), R5 (16) | UC-06 exc 2 (`uc05-uc06.spec.js`, `test.fail`); stored state of M3K05 read via API |
| **D-02** | Negative manual payment amount is accepted as a **confirmed** payment of −0.01 | **Major** | **High** | New → Triaged | **Fix before release** (same fix pattern as D-01). | Input validation | R15 | UC-05 probe H2 (`test.fail`); stored state of M3P06 |
| **D-03** | Invalid input on the *Mark as paid* form (e.g. amount `abc`) silently redirects to the order with no error message | Major (usability) | Medium | New → Triaged | **Fix before release** if possible; workaround: the order still shows *Pending*. Same root cause as Tawassul's UC-01 exc 1 (precision 20.001) — **one issue**, two reproductions. | Usability feedback | R2, R17 | UC-05 exc 1c (`test.fail`); `OrderTransition.post` falls through to `redirect()` |
| **D-04** | If a dependency fails after a payment is confirmed but before the order is marked paid, the order stays *pending* with a confirmed payment, and retrying the confirmation does nothing | **Major** | Medium | New → Triaged | **Fix or document a recovery runbook before release.** Needs a failure to occur, but leaves an inconsistent order that blocks the customer's ticket. | Transaction integrity | R2 (20), R6 (15), R16 | REC-02 / REC-02b (`test_recovery.py`, strict xfail) |
| **D-05** | Anti-phishing origin check logs every login as a possible phishing attempt when pretix runs on a non-default port | Minor | Low | New → Triaged | **Defer** (operational noise, no data impact); quick fix available. | Security monitoring / configuration | R21 | 68 log lines in one run (`security/server-log-bad-origin.txt`); `control/views/auth.py:170` |
| U-01 | Date picker silently replaces an unparseable typed date with today's date | Minor | Low | New → Triaged | **Defer**; document in user guide. | Usability feedback | R17 | UC-05 observation U-01 |
| SEC-F1 | Vendored Bootstrap 3.4.1 and moment 2.29.1 have published CVEs | Minor | Medium | New → Triaged | Plan upgrade; no exploit path found in W1/W2 pages. | Dependencies | R19 | ZAP Vulnerable JS Library |
| SEC-F2 | CSP lacks `form-action` | Minor | Low | Triaged | Defer to hardening backlog. | Security headers | R19 | ZAP 10055 |
| SEC-F3 | `X-Content-Type-Options` only set by the reverse proxy | Minor | Low | Triaged | Defer; document deployment requirement. | Security headers | R18 | ZAP 10021, `deployment/docker/nginx.conf:27` |
| SEC-F4 | `oauthlib 3.3.1` advisories (CVE-2026-49265, CVE-2026-49272) | Minor (for W1/W2) | Medium | Triaged | Upgrade with `django-oauth-toolkit`; not reachable from the Orders workflows. | Dependencies | R20 | `audit/pip-audit.json` |

Accessibility issues A1–A11 are tracked in `a11y-findings.md`; A1–A8 were fixed and verified, A9–A11 remain open (S1-specific, moderate/serious).

Re-test plan: every defect has an automated test that currently fails for the right reason (D-01..D-03 `test.fail`, D-04 strict `xfail`). When a fix lands, the test starts passing, Playwright/pytest reports "expected to fail but passed", and the marker must be removed — this is how *Verified* is recorded.

## 2. Root cause analysis — D-01 (negative cancellation fee accepted)

**5 Whys**
1. *Why was the order left paid with a total of −0.01?* Because the cancellation was executed with `cancellation_fee = −0.01`: `_cancel_order` canceled the positions, created a −0.01 fee and set `order.total = cancellation_fee`; since 20.00 paid ≥ −0.01 the status stayed *paid*.
2. *Why did the service accept −0.01?* `if cancellation_fee:` treats any non-zero value, including a negative one, as "keep a fee", and the only check is `cancellation_fee > order.total` (`base/services/orders.py:577, 627`).
3. *Why did the form let it through?* `CancelForm.cancellation_fee` sets `max_value = order.total` and `clean_cancellation_fee` checks only `val > total` (`control/forms/orders.py:170-220`); there is no `min_value`. The API field (`api/views/order.py:458`) has the same gap.
4. *Why was only the upper bound implemented?* The rule was written as "the fee cannot be higher than the total" — the lower bound (fee ≥ 0) was implicit and never stated as a requirement, so no layer owned it.
5. *Why was it not caught by tests?* Existing tests exercise fees within and above the total, but no boundary-value test probes just below the lower limit (−0.01 / 0.00); validation is duplicated per entry point (form, API) instead of being enforced once in the domain service.

**Root cause:** an unstated lower bound in the fee rule, combined with validation placed only in the entry-point layers (form and API) while the domain service trusts its callers.

**Fishbone (Ishikawa)** — effect: *negative fee persisted*

```
Requirements ── fee range written as "≤ total" only; lower bound implicit
Design ──────── validation in each entry point; _cancel_order trusts callers
Code ────────── no min_value on form/API fields; `if cancellation_fee:` true for negatives
Testing ─────── BVA only at the upper limit; no −0.01 / 0.00 cases
Process ─────── review checklist has no "both bounds of every numeric input"
Tools ───────── no property-based / generated boundary data for money fields
                                                    ──────────▶  NEGATIVE FEE STORED
```

**Corrective actions:** add `min_value=Decimal('0.00')` to `CancelForm.cancellation_fee` and to the API `cancellation_fee` field; raise `OrderError` in `_cancel_order` when `cancellation_fee < 0`; run a data check for existing orders with negative cancellation fees. Verify with UC-06 exc 2 (remove `test.fail`) and the API BVA tests.
**Preventive actions:** state the full valid range (both bounds and precision) of every monetary input in the test basis; enforce business invariants in the domain service, not only in forms; make "test just below, at and just above **both** bounds" a review-checklist item; add a custom mutation operator that removes/relaxes the lower-bound check so a missing test is visible. The same pattern produced **D-02** (`MarkPaidForm.amount` has no minimum), so the preventive action covers a class of defects, not one bug.

## 3. Root cause analysis — D-04 (order left pending after a failed confirmation)

**5 Whys**
1. *Why is the order pending although its payment is confirmed?* The failure (audit log unavailable) happened after the payment had been saved as *confirmed* but before the order status *paid* was saved.
2. *Why was the confirmed payment not rolled back with the order?* `OrderPayment.confirm()` uses **two separate** `transaction.atomic()` blocks: the first commits the payment state, the second runs `_mark_order_paid` (`base/models/orders.py:1890-1956`).
3. *Why are they separate?* The first block locks and confirms the payment quickly to resolve races with payment-provider callbacks ("Race condition detected" guard); the slower order step (quota check, invoice, signals, plugins, logging) runs afterwards.
4. *Why does a retry not repair it?* The race guard returns early whenever the payment is already confirmed; it assumes the order step succeeded too.
5. *Why is the inconsistency not detected?* There is no invariant check or reconciliation ("confirmed payments ≥ total ⇒ order paid") and no fault-injection test of the step between the two transactions.

**Root cause:** a two-phase state change without an idempotent completion step — the early-return guard conflates "payment confirmed" with "order paid".

**Fishbone** — effect: *confirmed payment on a pending order*

```
Design ──────── two transactions; idempotency keyed on payment state only
Code ────────── early return in confirm() when state == confirmed
Dependencies ── signal receivers, plugins, audit log and invoicing can raise in phase 2
Testing ─────── success paths only; no fault injection between the phases
Operations ──── no reconciliation job or alert for paid-but-pending orders
Requirements ── no explicit idempotency / recovery requirement for payment confirmation
                                                    ──────────▶  PARTIAL STATE, RETRY IGNORED
```

**Corrective actions:** in `confirm()`, when the payment is already confirmed but the order is not paid and the confirmed sum covers the total, run `_mark_order_paid` instead of returning (makes the retry complete the work); provide an admin runbook — "Mark as paid" with amount 0.00 re-runs the order step without a duplicate payment (proven by REC-02c).
**Preventive actions:** keep the REC-xx fault-injection tests in CI; add a periodic consistency check for confirmed-payment/pending-order mismatches; for every multi-transaction state change, require a design note on what happens if the process stops between transactions.

## 4. Pareto analysis

**Defects and weaknesses by category (Member 3 scope, 10 items)**

| Category | Items | Share | Cumulative |
|---|---|---|---|
| Input validation | 2 (D-01, D-02) | 20 % | 20 % |
| Usability feedback | 2 (D-03, U-01) | 20 % | 40 % |
| Dependencies | 2 (SEC-F1, SEC-F4) | 20 % | 60 % |
| Security headers | 2 (SEC-F2, SEC-F3) | 20 % | 80 % |
| Transaction integrity | 1 (D-04) | 10 % | 90 % |
| Security monitoring / configuration | 1 (D-05) | 10 % | 100 % |

By count the categories are flat, so weight by severity (Major = 3, Minor = 1): input validation 6, usability feedback 4, transaction integrity 3, dependencies 2, security headers 2, monitoring 1 → **input validation + usability feedback + transaction integrity = 13 of 18 points (72 %)**. These three are where test effort and fixes pay off most, and all three come from the payment/cancellation forms and services of W1/W2.

**Accessibility issues by rule (baseline, 59 unique issues)**

| Rule | Issues | Share | Cumulative |
|---|---|---|---|
| region | 25 | 42 % | 42 % |
| link-name | 12 | 20 % | 63 % |
| color-contrast | 6 | 10 % | 73 % |
| image-alt | 3 | 5 % | 78 % |
| html-has-lang | 3 | 5 % | 83 % |
| link-in-text-block | 3 | 5 % | 88 % |
| landmark-one-main | 3 | 5 % | 93 % |
| landmark-unique | 3 | 5 % | 98 % |
| heading-order | 1 | 2 % | 100 % |

Two rules account for 63 % of the issues, and both were fixed by a few lines in the shared layout (`<main>` landmark, labelled sub-menu links) — the Pareto view is why the fix targeted the layout rather than individual pages.
