# Member 3 — how to reproduce every result

Areas: use cases UC-05/UC-06, usability and accessibility, defensive security, performance and recovery.
Reports in this folder: `security-assessment.md`, `a11y-findings.md`, `performance-recovery.md`, `defects-and-rca.md`, `test-management.md`. Plan: `Documents/Member3-Plan.md`. Specs: `sqe/use-cases/UC-05.md`, `UC-06.md`. Evidence: `sqe/evidence/member3/`.

## Tool versions (as used for the committed evidence)

| Tool | Version | How it was obtained |
|---|---|---|
| Windows | 11 Pro build 26300 | — |
| Python / Django / pytest / coverage.py | 3.12.10 / 5.2.19 / 9.2.0 / 7.17.5 | `uv venv local\sqe\venv` + `uv pip install -e ".[dev]" pip-audit` |
| Node / npm | 24.18.0 / 11.16.0 | installed (matches `.node-version` 24) |
| Playwright / Chromium | 1.65.1 / 159.0.8154.6 (build 1255) | `src/tests/team/e2e/package.json` (exact pin) |
| axe-core / @axe-core/playwright | 4.14.1 / 4.14.0 | exact pin in `package.json` |
| Lighthouse | 13.6.0 | exact pin in `package.json` |
| OWASP ZAP | 2.17.0 (cross-platform zip) | `local/sqe/tools/ZAP_2.17.0`, run with Temurin JRE 21.0.13.1 |
| Grafana k6 OSS | 2.4.0 | `local/sqe/tools/k6-v2.4.0-windows-amd64/k6.exe` |
| pip-audit | 2.10.1 | in the project venv |

Portable tools are not committed (they live in the git-ignored `local/` folder). Download: k6 from `github.com/grafana/k6/releases` (v2.4.0 windows-amd64 zip), ZAP from `github.com/zaproxy/zaproxy/releases` (2.17.0 Crossplatform zip), JRE from `api.adoptium.net` (Temurin 21 JRE zip). Unzip each into `local/sqe/tools/`.

## Commands (PowerShell, from the repository root)

Reset and start (every mutating suite needs fresh fixtures; the server must be stopped before a reset):
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\sqe\m3-fresh-server.ps1    # stop server + reset 34 orders
powershell -NoProfile -ExecutionPolicy Bypass -File .\sqe\windows.ps1 serve       # leave running in its own window
```

Browser suites (UC-05/06, usability, access matrix):
```powershell
$env:SQE_REUSE_SERVER = '1'; $env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\local\sqe\browsers"
Push-Location src\tests\team\e2e
npm.cmd ci; npm.cmd exec -- playwright install chromium
npm.cmd exec -- playwright test uc05-uc06.spec.js access.spec.js --project=chromium
Pop-Location
```
Expected: UC suite 11 passed + 3 expected failures (D-01, D-02, D-03); access suite 14 passed.

Accessibility (read-only, no reset needed):
```powershell
Push-Location src\tests\team\e2e
$env:A11Y_PHASE = 'after'; $env:A11Y_FIXED_SCREEN = 'S3-cancel-form'
npm.cmd exec -- playwright test a11y.spec.js --project=chromium
node tools\lighthouse.mjs after
node tools\merge-a11y.mjs after
Pop-Location
```
To reproduce the *before* numbers, check out the commit before `fix(control): make the control-panel layout accessible…`, restart the server, and use `before`.

ZAP passive scan (safe mode, no active scan):
```powershell
$env:JAVA_HOME = "$PWD\local\sqe\tools\jdk-21.0.13.1+2-jre"; $env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
Start-Process java -ArgumentList '-Xmx1g','-jar','local\sqe\tools\ZAP_2.17.0\zap-2.17.0.jar','-daemon','-host','127.0.0.1','-port','8090','-dir','local\sqe\tools\zap-home','-config','api.disablekey=true'
Invoke-RestMethod 'http://127.0.0.1:8090/JSON/core/action/setMode/?mode=safe'
# reset + serve, then run the browser suites with:  $env:ZAP_PROXY = 'http://127.0.0.1:8090'
Invoke-RestMethod 'http://127.0.0.1:8090/JSON/core/view/numberOfMessages/?baseurl=http://127.0.0.1:18081'   # must be > 0
Invoke-WebRequest 'http://127.0.0.1:8090/JSON/core/view/alerts/?baseurl=http://127.0.0.1:18081' -OutFile zap-alerts.json
```

Dependency audit:
```powershell
.\local\sqe\venv\Scripts\pip-audit.exe --path .\local\sqe\venv\Lib\site-packages --format json --output pip-audit.json
npm.cmd audit --json > npm-audit-root.json
```

Recovery tests:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\sqe\windows.ps1 recovery    # 4 passed, 1 xfailed (D-04)
```

Performance (stop everything else first; DEBUG-off server):
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\sqe\m3-fresh-server.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\sqe\windows.ps1 serve-perf   # own window
$k6 = '.\local\sqe\tools\k6-v2.4.0-windows-amd64\k6.exe'
& $k6 run -e VUS=1 --summary-export run-1vu-a.summary.json --out json=run-1vu-a.raw.json src\tests\team\perf\order-read.k6.js
# repeat for 1vu-b, then VUS=5 for 5vu-a and 5vu-b
python sqe\m3_perf_summary.py <folder with the run files>
```

Before committing a Playwright HTML report: `python sqe\m3_sanitize_report.py <report folder>` (masks the test accounts' passwords and tokens and fails if any remain).

## Viva live-task quick reference

Business-rule constants for the browser tests are in `src/tests/team/e2e/rules.js`. Example: if the fee cap changes from 100 % to 50 % of the total, `FEE_CAP`/`FEE_BELOW_CAP`/`FEE_ABOVE_CAP` change to 10.00/9.99/10.01, and these tests are expected to fail until the product and the constants change: UC-06 exc 1 / USA-02 (19.99 would be rejected), plus the team's BR-03 unit tests, Member 2's API BVA tests and the mutation check that targets the fee comparison.
