# AMD ACT III — Intelligent Industry

Repository foundation for an industrial maintenance-reporting prototype proposed for AMD Developer Hackathon: ACT III, Track 1: Intelligent Industry. The repository currently contains planning, architecture, contribution guidance, and repository-integrity checks. It does not yet contain an application, trained model, evaluation results, or a deployed service.

## Product direction

The proposed MVP turns maintenance work-order exports into traceable, supervisor-approved reports. An operator uploads CSV/XLSX exports; a mapping assistant proposes column mappings for review; an extraction model suggests component, fault, and action annotations with source provenance; a supervisor approves or corrects them; deterministic code computes counts and retrieves related work orders; an LLM drafts report language from those computed facts; a claim checker binds numeric statements to approved facts before a PDF is produced. See [the proposal](docs/PROPOSAL.md) and [architecture](docs/ARCHITECTURE.md).

Future thermal-image anomaly detection is a separate research phase that requires real, labeled machine data and controlled evaluation. Later failure prediction requires validated linkage to outcomes and time-aware data. The MVP does not ingest live telemetry, prescribe repairs, or infer sensor-to-work-order links.

## Current state and workflow

This is a documentation and repository foundation. Proposed technology choices and future acceptance criteria are identified as proposals throughout the docs. No GPU-hour allocation, model compatibility, hosting price, benchmark score, or user interface is claimed as verified.

For contributors, read [CONTRIBUTING.md](CONTRIBUTING.md), then run the repository checks:

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python scripts/check_repository.py
```

The CI job named **Repository checks** runs these same commands. It validates Markdown targets and YAML/JSON syntax; it does not validate provider schemas, test the future product, or perform security scanning.

Use the tracked `.gitignore` for shared exclusions such as environments, secrets, datasets, uploads, reports, and model artifacts. Add personal, machine-specific ignore patterns to `.git/info/exclude`; that file stays local and is not shared with the team.

## Repository map

- [Proposal and milestones](docs/PROPOSAL.md)
- [System architecture](docs/ARCHITECTURE.md)
- [Deployment preparation](docs/DEPLOYMENT.md)
- [Contribution workflow](CONTRIBUTING.md)
- [Project-specific agent rules](AGENTS.md)
- [Security and data handling](SECURITY.md)
- [MIT license](LICENSE)

## Challenge submission note

The challenge information reviewed for this proposal identifies Track 1 as Intelligent Industry and requires a public GitHub repository and demo URL for final submission. This repository is intended to remain private during preparation; making it public requires a separate, explicit decision. Current challenge schedule and eligibility details can change; see the [challenge page](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii) and [live event page](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/live).
