# Local connected workspace and test handoff

Run the commands below in **PowerShell on this Windows computer**, from the repository root:

```powershell
Set-Location 'D:\Coding\Prj\AMDHACKIII\IGNIS-backend-mission'
.\scripts\start_local.ps1
```

If services are already running from this launcher, open the workspace directly. `outputs/local-session.json` records their process IDs, log directory and database location. The launcher refuses occupied ports and existing session records; it never resets older demo data. Frontend dependencies must be installed with `npm ci` in `frontend` first; Node.js and uv must be installed.

- Workspace: http://127.0.0.1:5173/#/app
- Landing page: http://127.0.0.1:5173/
- Proxied backend health: http://127.0.0.1:5173/api/health
- Direct backend health: http://127.0.0.1:8765/health

The default is **recorded replay**, using the committed six-record synthetic input and synthetic fixture evidence. It needs no AMD key and makes no live model calls. The connected workspace uses backend data, while the landing-page embedded mock remains a design preview. Provider and synthetic/mode labels are separate from human approval.

## Your first manual run

1. Choose **Load recorded demo input**. Confirm the proposed mapping, then continue to Review.
2. Click **Start extraction**. Inspect all six original rows and suggestions. The recorded-demo checkbox explicitly uses simulated record-review attribution so the historical explanation can be reproduced. Save each decision: five valid suggestions are accepted; the invalid one defaults to rejected. No record is automatically approved.
3. Continue to Facts and click **Analyze approved records** with `seal`, multiplier `3` and the recorded synthetic policy. Inspect facts, source-record references and alerts.
4. Continue to Evidence. Retrieve with `PUMP-SYN-01`, `seal`, `seal leakage flush`; inspect applicable passages and excluded sources. Generate the recorded explanation.
5. Enter an expert review reason. Leave **Simulated demonstration signoff** checked for this rehearsal, then save the decision. It is visibly not a real expert approval.
6. Continue to Report. Issue and download the actual backend PDF. Open every PDF page to check clipping, source labels and citations. Reload the browser: the saved run and decisions must survive.

Replay is exact-input playback. Changing the operator/mapping identity, record-review identity or revision, criticality, query or corpus can change snapshot/pack IDs and cause a replay miss. This must appear as an unavailable/invalid draft, never as a silently substituted live response. Use the facts-only path where allowed, or enter an explicit manually authored cited draft. User-supplied document reading/review/publishing remains a separate CLI workflow in the [API contract](API_CONTRACT.md).

## Automated checks for you to execute

### Backend HTTP replay

```powershell
uv run --no-project --with-requirements requirements-dev.txt python scripts/check_local_replay.py --base-url http://127.0.0.1:5173/api --out outputs/manual-api-e2e
```

This creates a synthetic run through actual HTTP, checks stale revisions and signoff gates, downloads the PDF, and saves JSON state/trace/results. It is a backend HTTP rehearsal, not a browser test or live model benchmark. Use a new output directory for a new evidence capture.

### Browser replay and injected failure boundaries

```powershell
.\scripts\run_browser_checks.ps1 -Headed
# Headless run with the installed Edge browser on Windows:
.\scripts\run_browser_checks.ps1
# Optional: download/use Playwright Chromium instead (also for machines without Edge):
.\scripts\run_browser_checks.ps1 -InstallBrowser -Headed
# Discover/type-check without running a browser journey:
Push-Location frontend
npm run test:e2e:list
Pop-Location
```

The suite uses installed Edge by default on Windows, or Playwright Chromium on other systems; `IGNIS_BROWSER_CHANNEL` can override that choice. It starts isolated replay services on **8776 and 5178**, with a new database under `outputs/browser-e2e` each invocation. It does not reset the interactive session on 8765/5173. It prepares desktop and 390 px/reduced-motion runs. The replay cases cover persisted review, actual PDF download, reference inspection, corrected-record invalidation, historical PDF preservation, and rejected/inconclusive expert decisions. `@mock-boundary` cases inject browser HTTP failures for 429, timeout and 409, rather than claiming a real provider outage. No automatic test retries are configured.

Results: `frontend/playwright-report` and `frontend/test-results`; failures retain screenshots and traces, and the happy path attaches run/mode/snapshot identity plus a screenshot. Open the report with `npm run test:e2e:report` from `frontend`. A listing/type-check is not a passing E2E run.

### Existing regression suite

```powershell
uv run --no-project --with-requirements requirements-dev.txt python -m unittest discover -s tests -v
uv run --no-project --with-requirements requirements-dev.txt python scripts/check_repository.py
```

## Restart, preserve and stop

```powershell
$session = Get-Content outputs/local-session.json -Raw | ConvertFrom-Json
.\scripts\stop_local.ps1
.\scripts\start_local.ps1 -ResumeDataDirectory $session.dataDirectory
uv run --no-project --with-requirements requirements-dev.txt python scripts/check_local_replay.py --base-url http://127.0.0.1:5173/api --out outputs/manual-api-e2e --verify-existing
# Stop when finished; database, PDFs and logs are preserved:
.\scripts\stop_local.ps1
```

## Acceptance still needed before the video

| Gate | Local preparation and remaining acceptance |
| --- | --- |
| Backend state/prompt regressions | Unit suite protects completed vs partial review, expert outcomes, report withdrawal and replay prompt identity. |
| Full L2 API checklist | HTTP rehearsal plus existing workflow tests cover key cases. Independently check mapping errors, invalid outputs, deduplication, absent/conflicting context, stale-report failure and complete provenance against #29. Do not infer complete coverage from the happy path. |
| L3 browser | Run the prepared suite, then inspect keyboard focus, all fact/passage references, 390 px layout, reduced motion and manual correction usability. Sounds are absent; no audio is required to understand state. |
| Scenario/quality review | Read [technical review](benchmarks/scenarios/TECHNICAL_REVIEW.md). All 20 contain ad-hoc fact schema differences. Expected answers and blind semantic ratings still need human approval. |
| Live inference | Not executed. Key stays in the Python environment only; the browser has no credential field. Live call enablement is session-local and off by default. Coordinate quota/window with UniverseScripts. |
| Deployment/product | Not performed by this local-only task. Choose the host/owner and provide persistent disk, long requests and same-origin routing (or deliberate CORS/auth). The current server remains loopback-only and single-operator. Run deployed smoke and inspect PDF/video/audio before recording the final video. |

Live explanations use prompt v3, chosen after two synthetic dev runs of v2 and v3, and the replay package is recorded with v3. See the [benchmark comparison](BENCHMARKS.md#v2-against-v3-and-the-default). Historical v1 timings and quality remain historical. No scenario, model result, expert review or human rating is silently reclassified as approved.
