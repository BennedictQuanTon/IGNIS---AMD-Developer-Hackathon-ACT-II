# Security and data handling baseline

This file records safe handling expectations; it does not claim a security audit or security scanning is enabled. The repository intentionally contains no security scanning workflow.

- Never commit credentials, access tokens, private maintenance exports, uploaded customer files, model checkpoints, or generated reports.
- Keep inference and storage credentials in server-side secret configuration; never place them in browser bundles or examples.
- Use synthetic or explicitly authorized, minimized data in development. Before operational exports are used, define access control, retention, deletion, backup, and incident handling.
- Avoid logging raw work-order content. Use request and record identifiers with bounded diagnostic details.
- Report suspected exposure privately to the repository maintainer; do not include sensitive content in a public issue.

The current CI workflow reads repository contents and runs documentation/configuration checks with read-only repository permissions. It does not scan dependencies, code, secrets, or vulnerabilities.
