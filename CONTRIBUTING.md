# Contributing

This repository contains the bounded maintenance backend and a separately developed UI preview. Product code should follow the architecture contracts and mark unverified behavior as proposed.

## Change workflow

1. Create a focused branch from `main` and describe the user-visible or documentation outcome.
2. Keep changes reviewable; update relevant architecture or proposal material when behavior or assumptions change.
3. Install checker dependencies with `python -m pip install -r requirements-dev.txt`, then run `python -m unittest discover -s tests -v` and `python scripts/check_repository.py` locally.
4. Open a pull request with context, validation performed, known limitations, and screenshots or sample outputs when relevant.
5. Wait for the required **Repository checks** status, resolve any review conversations, and merge manually using squash. An approving review or code-owner approval is optional.

Use clear commit messages, avoid committing secrets, private work-order exports, model weights, generated uploads/reports, or local environments, and keep dependency changes pinned and justified. This guidance describes the intended workflow; remote branch enforcement depends on repository plan and settings and must be verified by an administrator.

## Repository enforcement

The active [`main` ruleset](https://github.com/khanhtuongnakitomo/IGNIS/rules/24808628) requires pull requests, resolved review conversations and the strict **Repository checks** status. It requires zero approving reviews and no code-owner approval, enforces linear history, blocks force-pushes and branch deletion, and allows squash merges only. Repository administrators retain the existing always-bypass exception. Collaborators can merge their pull requests manually after checks pass; auto-merge is not required. When the frontend is present, the required check also typechecks and builds it.

## Documentation conventions

Distinguish implemented behavior from proposed design, measured results from targets, and source-document claims from reproduced evidence. Cite primary sources next to claims that depend on them. Explain evaluation split, metric, model/data version, and limitations whenever reporting a score.
