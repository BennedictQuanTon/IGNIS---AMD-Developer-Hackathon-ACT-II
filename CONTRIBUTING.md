# Contributing

This repository is currently a documentation and repository-check foundation. Product code should follow the architecture contracts and mark unverified behavior as proposed.

## Change workflow

1. Create a focused branch from `main` and describe the user-visible or documentation outcome.
2. Keep changes reviewable; update relevant architecture or proposal material when behavior or assumptions change.
3. Install checker dependencies with `python -m pip install -r requirements-dev.txt`, then run `python -m unittest discover -s tests -v` and `python scripts/check_repository.py` locally.
4. Open a pull request with context, validation performed, known limitations, and screenshots or sample outputs when relevant.
5. Resolve review conversations and obtain the required approval before merging. Do not merge unreviewed changes to `main`.

Use clear commit messages, avoid committing secrets, private work-order exports, model weights, generated uploads/reports, or local environments, and keep dependency changes pinned and justified. This guidance describes the intended workflow; remote branch enforcement depends on repository plan and settings and must be verified by an administrator.

## Repository enforcement

The active [`main` ruleset](https://github.com/khanhtuongnakitomo/AMDHACKACTIII/rules/24808628) requires one approval including code-owner review, dismisses stale approvals after new commits, requires review conversations to be resolved and the strict **Repository checks** status, enforces linear history, blocks force-pushes and branch deletion, and allows squash merges only. Repository administrators have an always-bypass exception for bootstrap and recovery. The normal team workflow remains pull request review and approval before merging.

## Documentation conventions

Distinguish implemented behavior from proposed design, measured results from targets, and source-document claims from reproduced evidence. Cite primary sources next to claims that depend on them. Explain evaluation split, metric, model/data version, and limitations whenever reporting a score.
