import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mock_chat_server import ScriptedServer, reply
from sample_data import pdf_bytes
from PIL import Image

from ignis_wo.documents.cache import ParseCache, artifact_key
from ignis_wo.documents.chunks import chunk_artifact
from ignis_wo.documents.contracts import DocumentArtifact, PageText, ReaderIdentity, SourceDocument
from ignis_wo.documents.ingest import ingest_document
from ignis_wo.documents.readers import native_identity
from ignis_wo.extraction.adapters import ReplayMiss
from ignis_wo.hosted.ocr import OcrClient, checked_pages
from ignis_wo.hosted.transport import Gateway, ProviderError

ROOT = Path(__file__).resolve().parents[1]
MODEL = "MinerU2.5-Pro"


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(buffer, "PNG")
    return buffer.getvalue()


def ocr_reply(*indices: int) -> dict:
    pages = [{"index": index, "markdown": f"Page {index}: seal leakage observed.", "images": []} for index in indices]
    return reply({"pages": pages, "model": MODEL, "usage_info": {"pages_processed": len(pages), "doc_size_bytes": 9}})


def ocr_client(server, model: str = MODEL, **options) -> OcrClient:
    return OcrClient(Gateway(server.base_url, "rc-test", sleep=lambda seconds: None), model, **options)


class DocumentTestCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.out = self.root / "documents"
        self.cache = ParseCache(self.root / "cache")

    def write(self, name: str, data: bytes) -> Path:
        path = self.root / name
        path.write_bytes(data)
        return path


class SourceTests(DocumentTestCase):
    def test_structured_exports_and_unknown_types_are_refused(self):
        with self.assertRaisesRegex(ValueError, "structured import"):
            ingest_document(self.write("export.csv", b"a,b\n"), "D-1", 1, "native", self.out)
        with self.assertRaisesRegex(ValueError, "unsupported"):
            ingest_document(self.write("notes.docx", b"x"), "D-1", 1, "native", self.out)

    def test_native_reader_reads_text_per_page_and_flags_pages_without_text(self):
        path = self.write("manual.pdf", pdf_bytes(["Seal leakage observed on PX-100.", "", "Inspect flush."]))
        artifact, _, _ = ingest_document(path, "MAN-1", 1, "native", self.out, pages=[0, 1])
        self.assertEqual([page.index for page in artifact.pages], [0, 1])
        self.assertIn("Seal leakage", artifact.pages[0].markdown)
        self.assertEqual(artifact.warnings, ["page 1: no text layer; read it with --reader mineru"])
        self.assertEqual((artifact.mode, artifact.status, artifact.review_status), ("native", "complete", "unreviewed"))

    def test_out_of_range_pages_and_native_images_are_refused(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            ingest_document(self.write("manual.pdf", pdf_bytes(["text"])), "MAN-1", 1, "native", self.out, [5])
        with self.assertRaisesRegex(ValueError, "no text layer"):
            ingest_document(self.write("scan.png", png_bytes()), "SCAN-1", 1, "native", self.out)

    def test_the_ocr_reader_needs_a_client(self):
        with self.assertRaisesRegex(ValueError, "DOCUMENT_OCR_MODEL"):
            ingest_document(self.write("scan.png", png_bytes()), "SCAN-1", 1, "mineru", self.out)


class OcrTests(DocumentTestCase):
    def test_a_pdf_request_carries_only_ocr_fields(self):
        path = self.write("manual.pdf", pdf_bytes(["text"]))
        with ScriptedServer([ocr_reply(0)]) as server:
            artifact, _, _ = ingest_document(path, "MAN-1", 1, "mineru", self.out, ocr_client=ocr_client(server))
        request = server.requests[0]
        self.assertTrue(request["path"].endswith("/ocr"))
        self.assertEqual(set(request["body"]), {"model", "document", "pages", "id"})
        self.assertEqual(request["body"]["document"]["type"], "document_url")
        self.assertTrue(request["body"]["document"]["document_url"].startswith("data:application/pdf;base64,"))
        self.assertEqual(request["body"]["pages"], [0])
        self.assertEqual((artifact.mode, artifact.usage["pages_processed"]), ("hosted_live", 1))

    def test_an_image_is_sent_as_an_image_url(self):
        with ScriptedServer([ocr_reply(0)]) as server:
            ingest_document(self.write("scan.png", png_bytes()), "SCAN-1", 1, "mineru", self.out,
                            ocr_client=ocr_client(server))
        document = server.requests[0]["body"]["document"]
        self.assertEqual(document["type"], "image_url")
        self.assertTrue(document["image_url"].startswith("data:image/png;base64,"))

    def test_malformed_empty_and_unrequested_pages_are_rejected(self):
        cases = [({"pages": "text"}, "invalid_response"), ({"pages": []}, "empty_output"),
                 ({"pages": [{"index": 3, "markdown": "x"}]}, "invalid_response"),
                 ({"pages": [{"index": 0}]}, "invalid_response")]
        for body, kind in cases:
            with self.assertRaises(ProviderError) as caught:
                checked_pages(body, [0, 1])
            self.assertEqual(caught.exception.kind, kind)

    def test_a_page_the_reply_leaves_out_makes_the_artifact_partial(self):
        path = self.write("manual.pdf", pdf_bytes(["one", "two"]))
        with ScriptedServer([ocr_reply(0)]) as server:
            artifact, _, _ = ingest_document(path, "MAN-1", 1, "mineru", self.out, ocr_client=ocr_client(server))
        self.assertEqual((artifact.status, artifact.missing_pages), ("partial", [1]))
        self.assertEqual(artifact.warnings, ["page 1: not returned by OCR"])


class CacheTests(DocumentTestCase):
    def test_a_repeat_read_makes_no_call_and_changed_inputs_miss(self):
        first = self.write("a.pdf", pdf_bytes(["one"]))
        second = self.write("b.pdf", pdf_bytes(["another"]))
        with ScriptedServer([ocr_reply(0)]) as server:
            ingest_document(first, "MAN-1", 1, "mineru", self.out, ocr_client=ocr_client(server), cache=self.cache)
            repeat, _, _ = ingest_document(first, "MAN-1", 1, "mineru", self.out, ocr_client=ocr_client(server),
                                           cache=self.cache)
            self.assertEqual((len(server.requests), repeat.mode), (1, "cache"))
            ingest_document(second, "MAN-1", 2, "mineru", self.out, ocr_client=ocr_client(server), cache=self.cache)
            ingest_document(first, "MAN-1", 1, "mineru", self.out, ocr_client=ocr_client(server, "Other-OCR"),
                            cache=self.cache)
        self.assertEqual(len(server.requests), 3)
        self.assertNotEqual(artifact_key("s", [0], native_identity()), artifact_key("s", [0, 1], native_identity()))

    def test_a_partial_read_is_not_cached_and_is_read_again(self):
        path = self.write("manual.pdf", pdf_bytes(["one", "two"]))
        with ScriptedServer([ocr_reply(0)]) as server:
            for _ in range(2):
                artifact, _, _ = ingest_document(path, "MAN-1", 1, "mineru", self.out, ocr_client=ocr_client(server),
                                                 cache=self.cache)
        self.assertEqual((artifact.status, artifact.mode, len(server.requests)), ("partial", "hosted_live", 2))

    def test_failed_and_empty_reads_are_not_cached(self):
        path = self.write("a.pdf", pdf_bytes(["one"]))
        with ScriptedServer([reply({"pages": []})]) as server, self.assertRaises(ProviderError):
            ingest_document(path, "MAN-1", 1, "mineru", self.out, ocr_client=ocr_client(server), cache=self.cache)
        blank = self.write("blank.pdf", pdf_bytes([""]))
        ingest_document(blank, "MAN-2", 1, "native", self.out, cache=self.cache)
        self.assertFalse(self.cache.directory.exists() and any(self.cache.directory.iterdir()))


class ReplayTests(DocumentTestCase):
    def test_a_recorded_read_replays_without_a_server(self):
        path = self.write("a.pdf", pdf_bytes(["one"]))
        record = self.root / "ocr-replay.jsonl"
        with ScriptedServer([ocr_reply(0)]) as server:
            live, _, _ = ingest_document(path, "MAN-1", 1, "mineru", self.out,
                                         ocr_client=ocr_client(server, record_path=record))
        replay_client = OcrClient(None, MODEL, replay_path=record)
        replayed, _, _ = ingest_document(path, "MAN-1", 1, "mineru", self.out, ocr_client=replay_client)
        self.assertEqual((replayed.mode, replayed.pages), ("hosted_replay", live.pages))
        with self.assertRaises(ReplayMiss):
            ingest_document(self.write("b.pdf", pdf_bytes(["two"])), "MAN-2", 1, "mineru", self.out,
                            ocr_client=replay_client)


class ChunkTests(unittest.TestCase):
    def test_tables_stay_whole_and_every_chunk_keeps_its_identity(self):
        table = "<table>\n" + "\n".join(f"<tr><td>WO-{index}</td><td>seal</td></tr>" for index in range(8)) + "\n</table>"
        markdown = f"Intro paragraph.\n\n{table}\n\nClosing note about the flush line."
        source = SourceDocument(document_id="MAN-1", revision=2, file_name="m.pdf", media_type="application/pdf",
                                sha256="ab" * 32, size_bytes=10)
        artifact = DocumentArtifact(artifact_id="DA-0123456789abcdef", source=source,
                                    reader=ReaderIdentity(reader="mineru", model_id=MODEL), requested_pages=[0, 1],
                                    processed_pages=[0, 1], missing_pages=[],
                                    pages=[PageText(index=0, markdown=markdown), PageText(index=1, markdown="Page two.")],
                                    mode="hosted_live", status="complete")
        chunks = chunk_artifact(artifact, max_characters=80)
        tables = [chunk.text for chunk in chunks if "<table>" in chunk.text]
        self.assertEqual(len(tables), 1)
        self.assertIn("</table>", tables[0])
        self.assertEqual(len({chunk.passage_id for chunk in chunks}), len(chunks))
        self.assertEqual(chunks[-1].passage_id, "MAN-1-r2-01234567-p001-c00")
        self.assertTrue(all(chunk.source_sha256 == source.sha256 for chunk in chunks))
        self.assertTrue(all(chunk.review_status == "unreviewed" for chunk in chunks))


class CommandTests(DocumentTestCase):
    def test_outputs_are_written_and_the_command_never_prints_document_text(self):
        path = self.write("manual.pdf", pdf_bytes(["Seal leakage observed on PX-100."]))
        command = [sys.executable, str(ROOT / "scripts" / "ingest_document.py"), str(path), "--document-id", "MAN-1",
                   "--revision", "1", "--reader", "native", "--out", str(self.out),
                   "--cache-dir", str(self.cache.directory)]
        completed = subprocess.run(command, capture_output=True, text=True, check=True, cwd=ROOT)
        summary = json.loads(completed.stdout)
        self.assertNotIn("Seal leakage", completed.stdout)
        directory = Path(summary["output"])
        self.assertEqual(sorted(file.name for file in directory.iterdir()), ["artifact.json", "chunks.jsonl", "original.pdf"])
        repeat = subprocess.run(command, capture_output=True, text=True, check=True, cwd=ROOT)
        self.assertEqual(json.loads(repeat.stdout)["mode"], "cache")


if __name__ == "__main__":
    unittest.main()
