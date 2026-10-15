"""Small stdlib HTTP JSON API bound to loopback; no credentials or progress are fabricated."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from ignis_wo.workflow.service import WorkflowStageError
from ignis_wo.workflow.store import Conflict, NotFound


def handler_for(workflow):
    class Handler(BaseHTTPRequestHandler):
        server_version = "IGNISLocal/1"

        def respond(self, status, payload, content_type="application/json"):
            body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def body(self):
            size = int(self.headers.get("Content-Length", "0"))
            if size > 8_000_000:
                raise ValueError("request body exceeds 8 MB")
            return json.loads(self.rfile.read(size) or b"{}")

        def do_GET(self):
            bits = [unquote(x) for x in self.path.split("?")[0].split("/") if x]
            try:
                if bits == ["health"]:
                    return self.respond(200, {"status": "ready", "storage": "sqlite", "scope": "single local operator"})
                if bits == ["runs"]:
                    return self.respond(200, {"runs": workflow.store.list()})
                if len(bits) >= 2 and bits[0] == "runs":
                    run_id = bits[1]
                    if len(bits) == 2:
                        return self.respond(200, workflow.get(run_id))
                    if bits[2] == "preview":
                        run = workflow.get(run_id)
                        preview = {"filename": run.get("filename"), "columns": run.get("columns", []), "rows": run.get("raw_rows", []), "row_count": run.get("row_count", 0), "mapping_proposal": run.get("proposal"), "row_issues": run.get("row_issues", [])}
                        return self.respond(200, preview)
                    if bits[2] == "history":
                        return self.respond(200, {"events": workflow.store.history(run_id)})
                    if bits[2] in {"facts", "alerts", "context", "reports"}:
                        run = workflow.get(run_id)
                        key = {"facts": "facts", "alerts": "alerts", "context": "context", "reports": "report_ids"}[bits[2]]
                        if bits[2] == "reports":
                            return self.respond(200, {"reports": [workflow.store.report(report_id) for report_id in run.get("report_ids", [])]})
                        return self.respond(200, {key: run.get(key)})
                    if bits[2] == "report" and len(bits) == 4:
                        report = workflow.store.report(bits[3])
                        if not report or report.get("run_id") not in {None, run_id}:
                            return self.respond(404, {"error": "report_not_found"})
                        return self.respond(200, Path(report["path"]).read_bytes(), "application/pdf")
                return self.respond(404, {"error": "not_found"})
            except NotFound:
                return self.respond(404, {"error": "run_not_found"})
            except WorkflowStageError as error:
                return self.respond(422, {"error": "stage_failed", "stage": error.stage, "message": str(error), "current_revision": error.run["revision"], "run": error.run})
            except Exception as error:
                return self.respond(400, {"error": "request_failed", "message": str(error)})

        def do_POST(self):
            bits = [unquote(x) for x in self.path.split("?")[0].split("/") if x]
            try:
                data = self.body()
                if bits == ["runs"]:
                    return self.respond(201, workflow.create_run(data.get("name", "Untitled"), data["operator"], data.get("synthetic", False), data.get("adapter_mode", "unavailable")))
                if len(bits) >= 2 and bits[0] == "runs":
                    run_id = bits[1]
                    if len(bits) == 3 and bits[2] == "upload":
                        return self.respond(200, workflow.upload(run_id, data["expected_revision"], data["filename"], data.get("csv_text"), data.get("content_base64")))
                    if bits[2:] == ["mapping", "confirm"]:
                        return self.respond(200, workflow.confirm_mapping(run_id, data["expected_revision"], data["mapping"], data["reason"]))
                    if bits[2:] == ["extraction", "start"]:
                        return self.respond(200, workflow.extract(run_id, data["expected_revision"]))
                    if len(bits) == 4 and bits[2] == "records":
                        return self.respond(200, workflow.review(run_id, data["expected_revision"], bits[3], data["status"], data["reason"], data.get("correction"), data.get("reviewer"), bool(data.get("demo_auto_review", False))))
                    if len(bits) == 3 and bits[2] == "analyze":
                        return self.respond(200, workflow.analyze(run_id, data["expected_revision"], data.get("criticalities")))
                    if len(bits) == 3 and bits[2] == "context":
                        return self.respond(200, workflow.build_context(run_id, data["expected_revision"], data.get("asset_id"), data.get("component"), data.get("query", "")))
                    if bits[2:] == ["context", "draft"]:
                        return self.respond(200, workflow.submit_draft(run_id, data["expected_revision"], data["draft"]))
                    if bits[2:] == ["context", "generate"]:
                        return self.respond(200, workflow.generate_context_draft(run_id, data["expected_revision"]))
                    if len(bits) == 3 and bits[2] == "expert-review":
                        return self.respond(200, workflow.expert_review(run_id, data["expected_revision"], data["decision"], data["reviewer"], data["reason"], data.get("corrected")))
                    if bits[2:] == ["reports", "issue"]:
                        return self.respond(200, workflow.issue_report(run_id, data["expected_revision"]))
                return self.respond(404, {"error": "not_found"})
            except Conflict as error:
                return self.respond(409, {"error": "revision_conflict", "message": str(error)})
            except NotFound:
                return self.respond(404, {"error": "run_not_found"})
            except WorkflowStageError as error:
                return self.respond(422, {"error": "stage_failed", "stage": error.stage, "message": str(error), "current_revision": error.run["revision"], "run": error.run})
            except KeyError as error:
                return self.respond(400, {"error": "missing_field", "field": str(error)})
            except Exception as error:
                return self.respond(422, {"error": "request_failed", "message": str(error)})

        def log_message(self, format, *args):
            return
    return Handler


def serve(workflow, host="127.0.0.1", port=8765):
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("local workflow API must bind to loopback")
    server = ThreadingHTTPServer((host, port), handler_for(workflow))
    print(f"IGNIS backend ready at http://{host}:{server.server_port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()
