# Member 3 — GitHub issues D-01 to D-05 (ready to paste)

How to file each one: on GitHub open `tawassulAkbr/pretix` → **Issues** → **New issue**. Copy the **Title** into the title box and the **Body** block into the description, add the labels, then **Submit new issue**. Write the issue number it gets (e.g. `#3`) into the "Filed as" line below and into the defect log (`defects-and-rca.md` §1).

Labels to create once (**Issues → Labels → New label**): `bug`, `severity: major`, `severity: minor`, `priority: high`, `priority: medium`, `priority: low`, `area: payments`, `area: cancellation`, `area: security`, `found-by: member3`.

Baseline for every issue: pretix `526a79c7d` on the team fork, tests on branch `zubair/develop`.

---

## Issue 1 — D-01

**Title:** `D-01: Negative cancellation fee is accepted and leaves a paid order with a negative total`
**Labels:** `bug`, `severity: major`, `priority: high`, `area: cancellation`, `found-by: member3`
**Filed as:** #___

**Body:**

````markdown
## Summary
When an Orders Manager cancels a paid order and keeps a cancellation fee of **-0.01**, pretix accepts it. The ticket positions are canceled, a -0.01 fee is stored, the order total becomes **-0.01**, and the order stays **paid**. This breaks business rule **BR-03** (0 ≤ fee ≤ order total) and requirement **CAN-03**.

## Environment
- pretix `526a79c7d` (team fork), Django 5.2.19, Python 3.12.10, SQLite, Windows 11
- Chromium 159 via Playwright 1.65.1
- Fixture order **M3K05** (paid, total 20.00), user: Orders Manager

## Steps to reproduce
1. Reset fixtures: `powershell -File .\sqe\m3-fresh-server.ps1`, then `.\sqe\windows.ps1 serve`.
2. Log in as the Orders Manager and open order M3K05 in the control panel.
3. Click **Cancel order**.
4. Enter **-0.01** in *Keep a cancellation fee of* and confirm with **Yes, cancel order**.
5. Read the order through the API (`GET /api/v1/organizers/<org>/events/<event>/orders/M3K05/`).

## Expected result
The form rejects the value with an error such as "The fee cannot be negative". Nothing changes: the order stays paid with total 20.00 and its positions are active.

## Actual result
The form accepts the value. Stored state: positions **canceled**, one fee of **-0.01**, order total **-0.01**, status **p** (paid).

## Severity / priority
**Major / High.** Creates negative revenue records and a wrong order state. Any manager typo (e.g. "-5") triggers it.

## Root cause (5 Whys summary)
- `CancelForm.cancellation_fee` (`src/pretix/control/forms/orders.py:170`) has only `max_value` (line 199); `clean_cancellation_fee` (line 216) checks only `fee > total`. There is no `min_value`.
- `_cancel_order` (`src/pretix/base/services/orders.py:577`) uses `if cancellation_fee:`, which is true for negative numbers. Its only check is `cancellation_fee > order.total` (line 627).
- The API path has the same gap (`src/pretix/api/views/order.py:456-459`).
- The lower bound was never written down as a requirement, so no layer enforced it.

Full RCA and fishbone diagram: `sqe/member3/defects-and-rca.md` §2.

## Suggested fix
- Add `min_value=Decimal('0.00')` to `CancelForm.cancellation_fee` and to the API field.
- Raise `OrderError` in `_cancel_order` when `cancellation_fee < 0`, so every entry point is protected.
- Check production data for existing orders with negative fees.

## Evidence / automated test
- `src/tests/team/e2e/uc05-uc06.spec.js:322`, test **"UC-06 exc 2 [known defect D-01] a negative cancellation fee is rejected (BVA just below zero)"**. It is marked `test.fail()` while this defect is open.
- Playwright report: `sqe/evidence/member3/playwright-report/`

## How to verify the fix
Remove `test.fail()` from that test and run `npx playwright test uc05-uc06.spec.js`. It must pass.

Related: D-02 (same root cause pattern).
````

---

## Issue 2 — D-02

**Title:** `D-02: Negative manual payment amount is saved as a confirmed payment`
**Labels:** `bug`, `severity: major`, `priority: high`, `area: payments`, `found-by: member3`
**Filed as:** #___

**Body:**

````markdown
## Summary
On **Mark as paid**, an amount of **-0.01** is accepted and stored as a **confirmed** payment of -0.01. A payment amount must be greater than zero (business rule **BR-01**, requirement **PAY-01**).

## Environment
- pretix `526a79c7d` (team fork), Django 5.2.19, Python 3.12.10, SQLite, Windows 11
- Chromium 159 via Playwright 1.65.1
- Fixture order **M3P06** (pending, total 20.00), user: Orders Manager

## Steps to reproduce
1. Reset fixtures and start the server (see D-01).
2. Log in as the Orders Manager and open order M3P06.
3. Click **Mark as paid**.
4. Enter amount **-0.01** and a valid payment date, then submit.
5. Read the order's payments through the API.

## Expected result
The form shows an error ("The amount must be greater than zero") and no payment is created.

## Actual result
A payment with amount **-0.01** and state **confirmed** is stored on M3P06.

## Severity / priority
**Major / High.** Creates false financial records that later affect refunds and reports.

## Root cause
`MarkPaidForm.amount` (`src/pretix/control/forms/orders.py:244`) has no minimum value, and the payment service trusts the form. This is the same pattern as D-01: only some bounds of a money field are checked, and only in the entry-point layer.

## Suggested fix
Add `min_value=Decimal('0.01')` to `MarkPaidForm.amount` (or reject ≤ 0 in `clean_amount`), and add the same check in the service or API layer.

## Evidence / automated test
- `src/tests/team/e2e/uc05-uc06.spec.js:181`, test **"UC-05 probe H2 [known defect D-02] a negative payment amount is rejected"**, marked `test.fail()`.
- Playwright report: `sqe/evidence/member3/playwright-report/`

## How to verify the fix
Remove `test.fail()` from that test and re-run the UC-05/06 suite. It must pass.

Related: D-01.
````

---

## Issue 3 — D-03

**Title:** `D-03: "Mark as paid" form gives no error message for invalid input and silently redirects`
**Labels:** `bug`, `severity: major`, `priority: medium`, `area: payments`, `found-by: member3`
**Filed as:** #___

**Body:**

````markdown
## Summary
If the **Mark as paid** form receives an invalid amount (e.g. `abc`, or a value with too many decimals such as `20.001`), pretix does not show the form again with an error. It redirects back to the order page without any message, so the manager does not know the payment was **not** recorded. (Usability: "errors must explain how to correct them".)

## Environment
- pretix `526a79c7d` (team fork), Chromium 159 via Playwright 1.65.1
- Fixture order **M3P04** (pending), user: Orders Manager

## Steps to reproduce
1. Reset fixtures and start the server.
2. Open order M3P04 and click **Mark as paid**.
3. Type `abc` in the *Payment amount* field, keep a valid payment date, and submit.

## Expected result
The form is shown again with an inline error next to the amount field, e.g. "Enter a number."

## Actual result
The browser is redirected to the order detail page with no error message. No payment is created and the order is still *Pending*, but the user is not told.

## Severity / priority
**Major (usability) / Medium.** Workaround: the order still shows *Pending*, so a careful user can notice.

## Root cause
In `OrderTransition.post` (`src/pretix/control/views/orders.py`), when the mark-paid form is invalid the code falls through to a plain `redirect()` instead of re-rendering the form with its errors.

Note: Tawassul's UC-01 exception 1 (precision `20.001`) is the **same defect**. File one issue and list both reproductions.

## Suggested fix
When the form is invalid, re-render the transition page with the bound form (or add a `messages.error(...)` with the form errors before redirecting).

## Evidence / automated test
- `src/tests/team/e2e/uc05-uc06.spec.js:145`, test **"UC-05 exc 1c [known defect D-03] a non-numeric payment amount shows an inline error"**, marked `test.fail()`.
- `uc05-uc06.spec.js:135` (exc 1b) confirms that no payment is created.

## How to verify the fix
Remove `test.fail()` from exc 1c and re-run the suite. It must pass.
````

---

## Issue 4 — D-04

**Title:** `D-04: Order stays pending with a confirmed payment if marking it paid fails, and retrying does nothing`
**Labels:** `bug`, `severity: major`, `priority: medium`, `area: payments`, `found-by: member3`
**Filed as:** #___

**Body:**

````markdown
## Summary
`OrderPayment.confirm()` saves the payment as **confirmed** in one database transaction and marks the order **paid** in a second one. If anything fails between them (here, the audit log write), the order is left **pending** with a **confirmed** payment. Calling `confirm()` again does not repair it: it returns early because the payment is already confirmed. The customer has paid but gets no ticket.

## Environment
- pretix `526a79c7d` (team fork), Python 3.12.10, pytest 9.2.0, SQLite
- Fault injection with `unittest.mock`: `Order.log_action` raises for `pretix.event.order.paid`

## Steps to reproduce
1. Run `powershell -File .\sqe\windows.ps1 recovery` (or `pytest src/tests/team/recovery`).
2. Test REC-02 creates a pending order, makes the audit log fail, and calls `payment.confirm()`.
3. REC-02b removes the fault and calls `payment.confirm()` again.

## Expected result
Either the whole confirmation rolls back (payment not confirmed, order pending), or a retry completes the order (status **paid**, still one payment).

## Actual result
After the failure: payment **confirmed**, order **pending** (partial state). After the retry: nothing changes. The order stays pending.

## Severity / priority
**Major / Medium.** It needs a failure to happen first, but then it blocks the customer's ticket and leaves inconsistent data.

## Root cause (5 Whys summary)
- `confirm()` (`src/pretix/base/models/orders.py:1890`) uses two separate `transaction.atomic()` blocks: line 1911 confirms the payment, line 1954 runs `_mark_order_paid`.
- The "Race condition detected" guard (line 1914) returns early whenever the payment is already confirmed. It assumes that the order step also succeeded.
- There is no reconciliation check of the form "confirmed payments ≥ total ⇒ order paid".

Full RCA: `sqe/member3/defects-and-rca.md` §3.

## Suggested fix
In `confirm()`, if the payment is already confirmed but the order is not paid and confirmed payments cover the total, run `_mark_order_paid` instead of returning. Until it is fixed, use this runbook: **Mark as paid** with amount 0.00 re-runs the order step without creating a duplicate payment (proven by test REC-02c).

## Evidence / automated test
- `src/tests/team/recovery/test_recovery.py:148` (REC-02, shows the partial state)
- `test_recovery.py:161` (REC-02b, `xfail(strict=True)`, the retry should complete the order)
- `test_recovery.py:167` (REC-02c, manual recovery works)
- JUnit result: `sqe/evidence/member3/recovery.xml`

## How to verify the fix
REC-02b will report **XPASS** and fail the run (strict). Remove the `xfail` marker. It must then pass.
````

---

## Issue 5 — D-05

**Title:** `D-05: Anti-phishing origin check ignores the port and logs every login as a possible phishing attempt`
**Labels:** `bug`, `severity: minor`, `priority: low`, `area: security`, `found-by: member3`
**Filed as:** #___

**Body:**

````markdown
## Summary
The login page reports its origin to `bad_origin_report`. The server builds the "good" origin from `SITE_URL` as `scheme + '://' + hostname`, which **drops the port**. When pretix runs on a non-default port (here `http://127.0.0.1:18081`), the browser sends `http://127.0.0.1:18081`, the strings never match, and **every** login writes a "Received report of unexpected origin value" warning. Real phishing warnings get lost in the noise.

## Environment
- pretix `526a79c7d` (team fork), `SITE_URL=http://127.0.0.1:18081`, Windows 11

## Steps to reproduce
1. Start the server on port 18081 (`.\sqe\windows.ps1 serve`).
2. Open the login page in a browser and log in.
3. Read the server log.

## Expected result
No warning, because the page was served from the configured site URL.

## Actual result
One warning per login page view: `Origin sent from JavaScript: http://127.0.0.1:18081 / Expected origin from configuration: http://127.0.0.1`. One test run produced **68** of these lines.

## Severity / priority
**Minor / Low.** No data impact, but it degrades security monitoring (alert fatigue). It does not occur on ports 80/443.

## Root cause
`src/pretix/control/views/auth.py:170`:
```python
good_origin = urlparse(settings.SITE_URL).scheme + '://' + urlparse(settings.SITE_URL).hostname
```
`hostname` excludes the port, while the browser's `window.location.origin` includes it.

## Suggested fix
Compare against `scheme + '://' + netloc` (which keeps a non-default port), or normalise both sides by removing default ports before comparing.

## Evidence
- `sqe/evidence/member3/security/server-log-bad-origin.txt`
- `sqe/member3/security-assessment.md` (finding D-05)
````

---

## After filing

1. Put each issue number in the "Filed as" lines above and in `defects-and-rca.md` §1.
2. Set the status in the defect log to *Triaged*.
3. When a fix lands and its test passes, comment on the issue with the test run, set it to *Verified*, then close it.
