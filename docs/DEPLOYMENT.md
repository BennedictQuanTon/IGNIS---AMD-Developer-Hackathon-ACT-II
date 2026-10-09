# Deployment preparation

There is no deployable application in this repository yet. This document is a target checklist, not evidence of a configured cloud account, GPU quota, running service, or cost estimate.

## Candidate topology

- Browser client talks to an authenticated application API over HTTPS.
- API, ingestion, deterministic analytics, review state, and report generation run in an application service.
- A private inference endpoint runs the selected open model on a confirmed AMD ROCm-capable host when available.
- A persistent database and protected object storage are selected before real maintenance exports are accepted.

A demo may use one application process and SQLite if concurrency and persistence limits are clearly stated. Keep provider keys and database credentials server-side. Do not expose the inference endpoint directly to an unauthenticated browser.

## Readiness gates

1. Reproduce environment setup from a clean checkout and lock runtime/dependency versions.
2. Confirm selected ROCm image, driver/runtime, model license, model revision, adapter behavior, structured-output support, memory use, and cold/warm latency on the actual host.
3. Exercise ingestion, review, deterministic snapshot, claim validation, PDF rendering, restart recovery, and per-record retry behavior with synthetic fixtures.
4. Choose identity, role permissions, retention/deletion, backup, logging, and operational-data handling before real exports are used.
5. Add a health endpoint that distinguishes API readiness from model readiness; bound inference timeouts and return actionable errors.
6. Record measured resource use and deployment costs from the chosen provider before estimating ongoing spend.
7. Test an end-to-end demo and provide a public demo URL only after the product and required repository visibility decision are approved.

No deployment workflow is included until there is an implemented application and selected target. The current GitHub action runs repository-integrity checks only.
