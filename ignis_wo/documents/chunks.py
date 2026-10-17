"""Splits page text into candidate chunks without losing page, revision or source identity.

Blocks are paragraphs separated by blank lines; an HTML table is one block. Blocks are never split,
so a table stays whole even when it is longer than the chunk limit.
"""

from ignis_wo.documents.contracts import CandidateChunk, DocumentArtifact


def page_blocks(markdown: str) -> list[str]:
    blocks, current, in_table = [], [], False

    def flush():
        text = "\n".join(current).strip()
        if text:
            blocks.append(text)
        current.clear()

    for line in markdown.splitlines():
        lowered = line.lower()
        if in_table:
            current.append(line)
            if "</table>" in lowered:
                flush()
                in_table = False
        elif "<table" in lowered:
            flush()
            current.append(line)
            in_table = "</table>" not in lowered
            if not in_table:
                flush()
        elif not line.strip():
            flush()
        else:
            current.append(line)
    flush()
    return blocks


def packed(blocks: list[str], max_characters: int) -> list[str]:
    chunks, current = [], []
    for block in blocks:
        size = sum(len(text) + 2 for text in current) + len(block)
        if current and size > max_characters:
            chunks.append("\n\n".join(current))
            current = []
        current.append(block)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def chunk_artifact(artifact: DocumentArtifact, max_characters: int = 1200) -> list[CandidateChunk]:
    source = artifact.source
    prefix = f"{source.document_id}-r{source.revision}-{artifact.artifact_id[3:11]}"
    chunks = []
    for page in artifact.pages:
        for index, text in enumerate(packed(page_blocks(page.markdown), max_characters)):
            chunks.append(CandidateChunk(
                passage_id=f"{prefix}-p{page.index:03d}-c{index:02d}", document_id=source.document_id,
                revision=source.revision, artifact_id=artifact.artifact_id, source_sha256=source.sha256,
                page_index=page.index, chunk_index=index, text=text, reader=artifact.reader))
    return chunks
