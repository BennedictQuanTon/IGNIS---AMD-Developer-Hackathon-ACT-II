"""Validate repository Markdown links and parse source YAML/JSON syntax."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", "site-packages",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "data", "datasets", "uploads",
    "outputs", "reports", "checkpoints", "models", "dist", "build", "coverage",
}


def source_files() -> list[Path]:
    found: list[Path] = []
    for current, dirs, names in os.walk(ROOT):
        dirs[:] = sorted(name for name in dirs if name not in SKIP_DIRS)
        found.extend(Path(current) / name for name in names)
    return sorted(found)


def markdown_files() -> list[Path]:
    return [path for path in source_files() if path.suffix.lower() == ".md"]


def check_markdown_links() -> list[str]:
    errors: list[str] = []
    for path in markdown_files():
        inside_fence = False
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if FENCE_RE.match(line):
                inside_fence = not inside_fence
                continue
            if inside_fence:
                continue
            for match in LINK_RE.finditer(line):
                target = match.group(1).strip().split(maxsplit=1)[0].strip("<>")
                parsed = urlsplit(target)
                if parsed.scheme or target.startswith("//") or not parsed.path:
                    continue
                link_path = unquote(parsed.path)
                candidate = (ROOT / link_path.lstrip("/")) if link_path.startswith("/") else (path.parent / link_path)
                candidate = candidate.resolve()
                try:
                    candidate.relative_to(ROOT)
                except ValueError:
                    errors.append(f"{path.relative_to(ROOT)}:{line_no}: link escapes repository: {target}")
                    continue
                if not candidate.exists():
                    errors.append(f"{path.relative_to(ROOT)}:{line_no}: missing link target: {target}")
    return errors


def check_configuration() -> list[str]:
    errors: list[str] = []
    files = source_files()
    for path in (path for path in files if path.suffix.lower() in {".yml", ".yaml"}):
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{path.relative_to(ROOT)}: invalid YAML: {exc}")
    for path in (path for path in files if path.suffix.lower() == ".json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.relative_to(ROOT)}:{exc.lineno}: invalid JSON: {exc.msg}")
    return errors


def main() -> int:
    errors = check_markdown_links() + check_configuration()
    if errors:
        print("Repository checks failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"Repository checks passed: links and configuration parsed across {len(markdown_files())} Markdown files.")
    print("These checks do not test product behavior or perform security scanning.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
