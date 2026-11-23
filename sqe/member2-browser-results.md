# Orders browser results · 23 November 2026

**All 20 Chromium cases passed.** Ten exercise Member 2's UC-03 and UC-04. Ten reran the shared UC-01 and UC-02 cases. Playwright reported zero failures, skips, retries or flaky tests. The run took 433 seconds and exited 0. [Sanitized results and journey readbacks](evidence/member2-browser.json)

The native Windows checkout started at `c5783c9a3` with the Member 2 working changes. It used CPython 3.12.10, Django 5.2.19, Node 24.19.0, Playwright 1.65.1 and Chromium headless shell 159.0.8154.6. The server used the loopback URL and disposable SQLite database from the Windows handoff. The reset seeded 65 orders. The API suite ran first on separate aliases. Chromium ran with one worker on its untouched browser fixtures.

| Journey | Before | After payment | After cancellation |
| --- | --- | --- | --- |
| FLW02 · UC-04-M | Pending, EUR 20.00, one active position | Paid, one confirmed EUR 20.00 manual payment | Canceled, dated, EUR 20.00 total, original position flag and payment, zero fees |
| FLW03 · UC-04-A1 | Pending, EUR 20.00, one active position | Paid, one confirmed EUR 20.00 manual payment | Paid, dated, EUR 5.00 total and cancellation fee, original position canceled, original payment |
| FLW04 · UC-04-A2 | Expired, EUR 20.00, one active position | Paid, one confirmed EUR 20.00 manual payment | Canceled, dated, EUR 20.00 total, original position flag and payment, zero fees |

For FLW05, the control panel displayed the quota error and recorded a failed attempt. FLW06 kept its confirmed payment and paid status after the fee-cap rejection. The rejected UC-03 fees preserved both paid orders. [Use cases and fixture IDs](use-cases/uc03-uc04.md) · [API findings](member2-api-results.md)

The first UC-04 main flow took 29.7 seconds against Playwright's 30-second default. The final spec allows 60 seconds for the multi-step journeys. After restoring the fresh snapshot, a filtered run with `--grep UC-04` passed all five in 2.2 minutes, including two that took over 30 seconds. The local report is `local/sqe/evidence/member2-uc04-repeat.json`.

## Reproduce the report

From the repository root, reset the fixtures and start the server using the [Windows handoff](handoff.md). In another PowerShell session run

~~~powershell
$env:SQE_REUSE_SERVER = '1'
$env:PLAYWRIGHT_JSON_OUTPUT_FILE = Join-Path (Get-Location) 'local/sqe/evidence/member2-browser.json'
$env:PLAYWRIGHT_HTML_OUTPUT_DIR = Join-Path (Get-Location) 'local/sqe/evidence/playwright-report'
$env:PLAYWRIGHT_HTML_OPEN = 'never'
npm.cmd --prefix src/tests/team/e2e test -- '--reporter=list,html,json'
~~~

The local HTML report opens from `local/sqe/evidence/playwright-report/index.html`. The tracked evidence includes case outcomes, timings and the three viewer readbacks from each successful UC-04 journey. Raw browser traces and local credentials stay in the ignored workspace.
