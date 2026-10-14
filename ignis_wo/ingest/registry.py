"""Chooses a parser by file extension and records which parser version read the file."""

from pathlib import Path

from ignis_wo.contracts import RawRow, SourceFile
from ignis_wo.hashing import sha256_bytes
from ignis_wo.ingest import parsers

PARSER_VERSION = "parsers-v1"

PARSERS = {
    ".csv": ("csv", parsers.read_csv),
    ".tsv": ("tsv", parsers.read_tsv),
    ".json": ("json", parsers.read_json),
    ".jsonl": ("jsonl", parsers.read_jsonl),
    ".xlsx": ("xlsx", parsers.read_xlsx),
}


def parse_file(path: Path) -> tuple[SourceFile, list[RawRow]]:
    extension = path.suffix.lower()
    if extension not in PARSERS:
        supported = ", ".join(sorted(PARSERS))
        raise ValueError(f"unsupported file type {extension!r}; supported: {supported}")
    parser_id, read_rows = PARSERS[extension]
    data = path.read_bytes()
    source_file = SourceFile(
        sha256=sha256_bytes(data),
        name=path.name,
        parser_id=parser_id,
        parser_version=PARSER_VERSION,
    )
    return source_file, read_rows(data)
