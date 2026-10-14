"""Writes one JSON artifact per stage plus a manifest, so a failure points to a stage."""

import json
from pathlib import Path

from ignis_wo.hashing import content_hash, to_plain


class StageFailed(Exception):
    def __init__(self, stage: str, errors: list[str]):
        self.stage = stage
        self.errors = errors
        super().__init__(f"stage {stage} failed: {'; '.join(errors[:5])}")


class StageWriter:
    def __init__(self, run_directory: Path):
        self.run_directory = run_directory
        self.run_directory.mkdir(parents=True, exist_ok=True)
        self.entries: list[dict] = []

    def write(self, stage: str, payload, input_hashes: list[str]) -> str:
        plain = to_plain(payload)
        output_hash = content_hash(plain)
        self.entries.append(
            {
                "stage": stage,
                "status": "succeeded",
                "artifact": self.save_artifact(stage, plain),
                "input_hashes": input_hashes,
                "output_hash": output_hash,
            }
        )
        self.save_manifest()
        return output_hash

    def fail(self, stage: str, errors: list[str], payload=None) -> None:
        entry = {"stage": stage, "status": "failed", "errors": errors}
        if payload is not None:
            entry["artifact"] = self.save_artifact(stage, to_plain(payload))
        self.entries.append(entry)
        self.save_manifest()
        raise StageFailed(stage, errors)

    def save_artifact(self, stage: str, plain) -> str:
        artifact_path = self.run_directory / f"{stage}.json"
        artifact_path.write_text(json.dumps(plain, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return artifact_path.name

    def save_manifest(self) -> None:
        manifest_path = self.run_directory / "manifest.json"
        manifest = {"stages": self.entries}
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
