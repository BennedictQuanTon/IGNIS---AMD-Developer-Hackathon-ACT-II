# Deployment preparation

The current application has a React/Vite frontend, a Python HTTP workflow API, SQLite state, file-backed reports and document artifacts, and AMD-hosted inference. The connected workspace is under active, uncommitted development. Local replay verification does not establish public deployment or live-provider readiness.

The older GPU, sensor-monitoring and scheduler proposals are future work, not prerequisites for the historical-work-order demo. See the [API contract](API_CONTRACT.md), [local run guide](LOCAL_RUN.md) and [benchmark limitations](BENCHMARKS.md).

## Proposed first deployment

Use one persistent host for a private, single-operator demo. This is a recommendation; no provider, account, paid plan or public URL has been selected.

| Part | Proposed arrangement | Reason |
| --- | --- | --- |
| HTTPS entry point | Reverse proxy serving the production frontend and forwarding `/api/*` to the loopback API, removing `/api` | Matches the local browser contract without cross-origin configuration |
| Frontend | Static files produced by `npm ci` and `npm run build` in `frontend` | Vite development and preview servers are local tools |
| Backend | One supervised Python process on loopback behind the proxy | The current API deliberately refuses public bind addresses and is intended for one operator |
| Storage | SQLite, uploaded files, corpus snapshots, PDFs and recordings on a protected persistent volume | Restarts must preserve state and the files referenced by that state |
| Model mode | Replay by default; live inference for an operator-controlled session | Preserves the shared API budget and repeatability |
| Access | Authentication at the HTTPS entry point covering static content, API and reports | The application has no built-in authentication or role enforcement |

A host requiring a public bind address cannot use the current server unchanged. Choose the same-host proxy arrangement above or implement and test a deliberate adaptation. Ephemeral/serverless storage does not suit the current SQLite-and-files design. Multi-user production operation requires a separate concurrency, identity and authorization design.

## Preparation order and acceptance

1. **Freeze the verified version.** Review existing changes and preserve the npm lockfile. Reproduce Python dependencies from `requirements-dev.txt` and frontend dependencies with `npm ci`. Commit/push require separate explicit authorization.
2. **Complete local acceptance.** Run the full Python suite, repository checks, production frontend build, browser tests and HTTP replay using the local guide. Stop/start with the same data directory and verify the issued PDF hash is unchanged. Inspect every PDF page. Count replay, injected browser failures and live results separately.
3. **Choose the host, access policy and owner.** Confirm persistent storage, HTTPS, supervision, backups, restore procedure and long-request support. The browser currently allows 300 seconds; align proxy timeouts with OCR/model requests and test a long response. Keep the backend port private.
4. **Stage replay privately.** Build with `VITE_API_BASE=/api`. Start `scripts/serve_hosted.py` with `--replay-dir docs/benchmarks/replay`, explicit `--db` and `--data` paths on the persistent volume, and the selected loopback port. Use repository-relative or absolute paths on that host. Add `--corpus` only when the walkthrough has matching reviewed evidence/recordings. The PowerShell launcher is for this Windows machine, not a cloud startup command.
5. **Verify staged URLs.** Check authenticated access, `/api/health`, upload/mapping, record decisions, facts, reference inspection, expert review and PDF download. Restart and verify saved state/PDFs; rehearse a backup restore. Confirm mode labels and server-side credentials. Test unauthenticated denial on API and PDF URLs too.
6. **Run a bounded live smoke separately.** Coordinate quota with UniverseScripts. Live extraction needs MaintIE to rebuild frozen few-shot examples. Keep the AMD key server-side. Record extraction, explanation and OCR results with exact configuration, latency, status and failures. V2 and opt-in v3 have preliminary synthetic dev measurements, not hosted product acceptance or human semantic approval. Review scenarios, missed abstentions and blind semantic ratings before quality claims.
7. **Publish after acceptance and authorization.** Deployment, public access, submission and final video are distinct actions. Local preparation does not create a cloud service or publish the project.

## Open gates

- Built-in authentication, roles and multi-user operation are absent. Restrict the first hosted demo at the proxy and use synthetic input until real-data controls are agreed.
- The stdlib HTTP server is a bounded local/demo implementation. Production needs an appropriate server lifecycle, request handling and capacity checks.
- Document ingestion/review/publishing use CLI tools; the browser accepts structured work-order exports.
- Replay is exact-input playback. Changed annotations, reviewer identity, query, criticality or corpus can miss recordings. Never substitute live inference silently.
- Scenario expected answers and blind ratings need human review. Structural validation does not prove semantic support or confirmed causation.
- Provider cost, deployment resource use, GPU throughput, real-factory accuracy and production savings have not been measured by local validation.

The GitHub workflow runs the Python unittest suite, repository checks and frontend typecheck/build. Browser E2E is a separate local check; a green GitHub badge alone does not establish browser acceptance.
