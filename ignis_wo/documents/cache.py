"""Content-addressed parse cache: identical bytes, pages and reader configuration never call OCR twice."""

from pathlib import Path

from ignis_wo.documents.contracts import DocumentArtifact, ReaderIdentity
from ignis_wo.hashing import content_hash


def artifact_key(source_sha256: str, pages: list[int], reader: ReaderIdentity) -> str:
    return "DA-" + content_hash({"sha256": source_sha256, "pages": pages, "reader": reader})


def has_text(artifact: DocumentArtifact) -> bool:
    return any(page.markdown.strip() for page in artifact.pages)


class ParseCache:
    def __init__(self, directory: Path):
        self.directory = directory

    def path_for(self, artifact_id: str) -> Path:
        return self.directory / f"{artifact_id}.json"

    def load(self, artifact_id: str) -> DocumentArtifact | None:
        path = self.path_for(artifact_id)
        if not path.exists():
            return None
        return DocumentArtifact.model_validate_json(path.read_text(encoding="utf-8"))

    def store(self, artifact: DocumentArtifact) -> bool:
        """Only complete artifacts with some text are kept: an empty, failed or partial read is never served
        as a hit, so reading it again retries OCR instead of returning the same missing pages."""
        if artifact.status != "complete" or not has_text(artifact):
            return False
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.path_for(artifact.artifact_id)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(path)
        return True
