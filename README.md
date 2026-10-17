# AMD ACT III — Intelligent Industry

Maintenance-intelligence prototype for AMD Developer Hackathon: ACT III, Track 1: Intelligent Industry. The repository now includes a local persistent work-order backend with explicit review, deterministic facts and alerts, scoped evidence packs and evidence-linked PDFs. See the [API guide and Windows startup commands](docs/API_CONTRACT.md). The seeded walkthrough uses synthetic fixtures and simulated signoff. Hosted AMD inference is measured on MaintIE and synthetic sets in the [benchmark report](docs/BENCHMARKS.md); deployment remains unverified.

## Product direction

**Current proposed system, confirmed 14 October 2026:** three loops and eleven logical parts connect hourly monitoring, human-approved incident response and offline model improvement. Read the [complete workflow and architecture comparison](docs/PROPOSED_SYSTEM_WORKFLOW.md) and the [architecture explained through the hospital analogy](artifacts/ignis-architecture-explained.html). Adoption of this direction does not mean the application is implemented or its benefits are measured. Earlier build schedules and detailed diagrams remain historical where they differ from this proposal.

The current API-based demo proposal is tracked in [issue #16](https://github.com/khanhtuongnakitomo/IGNIS/issues/16). Ownership is split into [backend #17](https://github.com/khanhtuongnakitomo/IGNIS/issues/17), [models and benchmarks #18](https://github.com/khanhtuongnakitomo/IGNIS/issues/18), and [UI/UX and E2E #19](https://github.com/khanhtuongnakitomo/IGNIS/issues/19). The [UI design preview in PR #20](https://github.com/khanhtuongnakitomo/IGNIS/pull/20) uses browser-local mock data; backend integration is a separate step.

The latest requested expansion adds problem recognition, forecasting, technician assignment and maintenance scheduling to reduce production loss. The [detailed maintenance direction](docs/MAINTENANCE_DIRECTION.md) defines the proposed layers, approval boundaries, dispatch example and implementation phases. These capabilities remain proposed; the revised [interactive architecture walkthrough](artifacts/ignis-data-flow.html) demonstrates synthetic flows and decisions locally. The [simplified high-level view](artifacts/ignis-high-level-architecture.html) shows the same system as eleven parts in three loops and adds the proposed fine-tuning role: LoRA adapters for work-order extraction and evidence-cited explanation, released only after held-out evaluation and approval.

The revised direction combines historical work orders with historical and simulated-live sensor information, RAG retrieval, and knowledge-graph-assisted reasoning to help assess machine condition. The user requested this scope change on October 13, 2026, and confirmed that the demonstration uses simulated data rather than a factory connection; a specific KAG framework remains open. The proposed example asset is a motor-driven pump with bearing temperature, vibration RMS and motor-current measurements, plus speed/load context. These sensor choices are design recommendations, not existing hardware or implemented sources. See [the proposal](docs/PROPOSAL.md) and [architecture](docs/ARCHITECTURE.md).

The work-order baseline remains: upload exports, review column mappings and model-suggested component/fault/action annotations, preserve provenance and revisions, compute exact facts, validate report claims, and render evidence-linked PDFs. The sensor extension adds timestamped observations, a condition-analysis service, a versioned asset/component/sensor graph, and retrieval from applicable documents and approved history. Numeric condition assessment belongs to rules or a validated model; RAG and graph reasoning supply context and cited explanations.

The combined design also continuously ingests machine logs and new/updated CSV/XLSX exports through checkpointed source adapters. Reviewed mappings route spreadsheet rows as telemetry, machine events or maintenance records. Exact sensor/event facts, approved work-order counts and historical triage remain distinct, while one version-pinned evidence pack connects them for checked explanations and reports. Continuous ingestion does not automatically approve work-order annotations or trigger an LLM call for every sample. Sources are simulated in the first demonstration.

The proposed demo supports historical playback and a simulated live stream, both visibly labeled synthetic. No actual telemetry collection or factory connection is configured. Real-world thermal-image analysis and failure prediction remain separate research phases requiring appropriate data and evaluation. Experts authorise inspection/repair scope; the model does not authorise repairs or control equipment. Sensor-to-work-order links require explicit asset/time/provenance evidence.

## Current state and workflow

The confirmed assessment loop collects data continuously and compares the previous completed hour with applicable healthy historical data once each hour. Deviations create an in-app alert and evidence-backed RAG/graph evaluation. Only validated expert-confirmed or corrected findings enter a versioned case knowledge base for future retrieval; uncertain/rejected diagnoses do not become confirmed facts. Adding cases does not automatically retrain the model or change the normal baseline. Hourly jobs, alerts and knowledge publication remain proposed, not running services.

The implemented slice is bounded to historical exports, explicit mapping and annotation review, deterministic work-order priority alerts, applicability-filtered context, expert-reviewed drafts and issued reports. SQLite retains runs and history through restart. The broader sensor, dispatch and fine-tuning architecture above remains proposed. Hosted inference is injectable but not configured; no GPU allocation, trained adapter or benchmark score is claimed.

For contributors, read [CONTRIBUTING.md](CONTRIBUTING.md), then run the repository checks:

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python scripts/check_repository.py
```

The CI job named **Repository checks** validates Markdown targets and YAML/JSON syntax and runs the Python behavior tests. When a frontend lockfile is present, it also installs its locked dependencies, typechecks and builds it. These checks do not establish live-provider quality or production readiness.

Use the tracked `.gitignore` for shared exclusions such as environments, secrets, datasets, uploads, reports, and model artifacts. Add personal, machine-specific ignore patterns to `.git/info/exclude`; that file stays local and is not shared with the team.

## Repository map

- [Proposal and milestones](docs/PROPOSAL.md)
- [System architecture](docs/ARCHITECTURE.md)
- [Proposed-system workflow and comparison](docs/PROPOSED_SYSTEM_WORKFLOW.md)
- [Deployment preparation](docs/DEPLOYMENT.md)
- [Contribution workflow](CONTRIBUTING.md)
- [Project-specific agent rules](AGENTS.md)
- [Security and data handling](SECURITY.md)
- [MIT license](LICENSE)

## Challenge submission note

The challenge information reviewed for this proposal identifies Track 1 as Intelligent Industry and requires a public GitHub repository and demo URL for final submission. This repository is intended to remain private during preparation; making it public requires a separate, explicit decision. Current challenge schedule and eligibility details can change; see the [challenge page](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii) and [live event page](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/live).
