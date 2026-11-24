# Member 2 Orders API coverage

## Reproduce the Windows run

From the repository root, use the shared environment described in the [Windows handoff](handoff.md). Stop the test server before resetting. The dedicated SQLite database, credentials and raw JUnit report stay under the ignored `local/sqe/` directory.

~~~powershell
python sqe/generate_orders_cases.py --check
python sqe/generate_orders_cases.py --revision --check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File sqe/windows.ps1 reset
powershell.exe -NoProfile -ExecutionPolicy Bypass -File sqe/windows.ps1 serve
~~~

In a second PowerShell session at the repository root run

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File sqe/windows.ps1 api
~~~

The runner enables the loopback suite and uses the manager and viewer tokens from the reset. The server uses an in-memory mail backend. Reset before each subsequent API run because successful requests consume their own fixtures.

## Coverage matrix

| Requirement / rule | Cases and persisted oracle |
| --- | --- |
| PAY-01, PAY-02 / BR-01 | Generated payment bodies and the pending/expired journeys. Check status, one confirmed manual payment for the outstanding balance, original positions, fees, total and refunds. A quota rejection must preserve the confirmed balance. |
| PAY-03 / BR-01 | Repeat W1 on the already-paid order. Expect 400 and the same payment identity, date and amount. |
| PAY-04, CAN-05 | Two eligible orders, anonymous and read-only writes. Check 401 and 403 respectively, with a fresh authorized GET after every denial. Successful generated actions cover both manager writes. |
| CAN-01, CAN-02 / BR-03/04 | Same-order W1 to W2 with no fee or EUR 5.00. Check cancellation date, status, total, fee, retained payment and original position IDs/flags. |
| CAN-03 / BR-03 | Generated cancellation bodies around zero, EUR 20.00, EUR precision and decimal capacity. Invalid input should return 400 and leave the business snapshot unchanged. |
| CAN-04 / BR-02 | Repeat no-fee cancellation on a canceled order, repeat retained-fee cancellation after its active positions disappear, and cancel a positionless order. Each should return 400 without additional writes. |
| Order reads | Generated organizer, event and code segments cover fixtures and missing resources. Query cases exercise the canceled-position filter on a retained-fee order. |

The dataset contains 39 path, 5 query and 35 body rows. The live suite sends 25 path rows. The other 14 cover nulls, omissions, non-string values and empty segments that cannot identify an order detail route. Length probes with valid syntax still return a missing-resource response because the fixture has no resource at that length. The seven additional scenario tests cover authorization, state, replay and quota. Repeated readbacks and fixture setup do not increase the test count.

The contract is scoped to JSON and the seeded EUR event. Mail delivery, concurrency/lock contention, other currencies, and alternate content types are outside this run. The two edits in the [dataset comparison](data/README.md) model a separate specification revision.

## Observed results · 23 November 2026

On native Windows with CPython 3.12.10, Django 5.2.19, pytest 9.2.0 and SQLite, the 72 tests produced **62 passes and 10 failures**, with zero skips. The API command exited 1. The tested checkout was `c5783c9a3` plus the Member 2 working changes. Both generation checks and asset compilation exited 0. The scoped server used port 18081 and a reset of 65 synthetic orders. The local JUnit file is `local/sqe/evidence/member2-api.xml`. [Sanitized case results](evidence/member2-api.json)

| Finding | Observed response and persisted state | Source explanation and proposed correction |
| --- | --- | --- |
| High · PAY-02 · R2/R3 | The exhausted-quota payment returned 400. The order remained expired with a confirmed EUR 20.00 manual payment. | The payment confirmation is saved before order admission checks. The REST exception handler returns 400 without reversing the confirmation. Make payment confirmation and order admission atomic for this action, or persist a failed attempt on rejection. |
| High · CAN-03 · R5 | The below-zero fee returned 200. The paid order had a canceled position, a negative fee and a total of EUR −0.01. | The fee field checks decimal capacity and the service enforces the upper cap. Enforce a nonnegative lower bound in the serializer and the shared service. |
| Medium · CAN-03 · R6 | An empty fee string returned 500. The business snapshot was unchanged. | The view skips the decimal field for falsy input and the service then tries to convert an empty string. Validate before invoking the service and return a field-level 400 for malformed values. |
| Medium · W1/W2 · R2 | Six requests with a non-boolean email setting returned 200 and paid or canceled their order. One cancellation with a numeric comment also succeeded. | The actions read raw body values. Validate the entire JSON body before changing order state and make any supported coercions explicit in the contract. |

The happy-path payments, both same-order cancellation branches, replay and access checks passed. The two malformed query-filter cases also completed with the default active-position view, consistent with the implementation's string comparison. The tests preserve the failing business assertions for subsequent fixes.

A second run at `65eca1d60` with the browser work in progress restored the fresh seeded SQLite snapshot and ran the same API command. The quota assertion permits a failed or unconfirmed attempt. The same ten cases failed, with 62 passes and zero skips in 21.27 seconds.

[API tests](../src/tests/team/api/test_orders_api.py) · [Actions](../src/pretix/api/views/order.py) · [Cancellation service](../src/pretix/base/services/orders.py)
