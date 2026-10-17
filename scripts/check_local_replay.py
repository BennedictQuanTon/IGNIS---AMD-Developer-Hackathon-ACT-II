"""Exercise the real local HTTP workflow with recorded model responses and simulated signoff.

This checks the HTTP backend only; run the browser suite separately for frontend/API integration.
No AMD credential or live model endpoint is used.
"""
import argparse
import hashlib
import io
import json
import subprocess
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pypdf import PdfReader


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--verify-existing", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    trace = []
    trace_path = args.out / ("restart-http-trace.json" if args.verify_existing else "http-trace.json")

    def call(method, path, body=None, expected=200):
        raw = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(args.base_url.rstrip("/") + path, data=raw, method=method,
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=30) as response:
                status, content, kind = response.status, response.read(), response.headers.get_content_type()
        except HTTPError as error:
            status, content, kind = error.code, error.read(), "application/json"
        payload = content if kind == "application/pdf" else json.loads(content)
        trace.append({"method": method, "path": path, "status": status})
        trace_path.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
        if status != expected:
            raise RuntimeError(f"{method} {path}: expected {expected}, got {status}: {payload}")
        return payload

    def persist_result(result):
        (args.out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        trace_path.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")

    assert call("GET", "/health")["status"] == "ready"
    if args.verify_existing:
        result = json.loads((args.out / "result.json").read_text(encoding="utf-8"))
        state = call("GET", f"/runs/{result['run_id']}")
        report = call("GET", f"/runs/{result['run_id']}/report/{result['report_id']}")
        assert state["latest_report"]["report_id"] == result["report_id"]
        assert hashlib.sha256(report).hexdigest() == result["pdf_sha256"]
        result["persistence_verified_after_restart"] = True
        persist_result(result)
        print(json.dumps(result, indent=2))
        return

    csv_text = (args.project / "docs/benchmarks/replay/demo_input.csv").read_text(encoding="utf-8")
    state = call("POST", "/runs", {"name": "Synthetic pump replay package", "operator": "synthetic-demo-operator",
                                   "synthetic": True, "adapter_mode": "injected"}, 201)
    run_id = state["run_id"]
    path = f"/runs/{run_id}"

    def step(suffix, extra=None):
        nonlocal state
        state = call("POST", path + suffix, {"expected_revision": state["revision"], **(extra or {})})
        return state

    step("/upload", {"filename": "synthetic-pump.csv", "csv_text": csv_text})
    assert call("GET", path + "/preview")["row_count"] == 6
    step("/mapping/confirm", {"mapping": state["proposal"]["mapping"], "reason": "synthetic headers"})
    step("/extraction/start")
    assert state["stage_status"]["extraction"] == "succeeded"
    usable = {s["record_id"] for s in state["suggestions"] if s["output"]}
    assert len(state["suggestions"]) == 6
    for record in state["records"]:
        decision = "accepted" if record["record_id"] in usable else "rejected"
        step("/records/" + record["record_id"], {"status": decision,
             "reason": f"SYNTHETIC replay package: {decision} without human review",
             "reviewer": "SYNTHETIC DEMO SIMULATOR"})
    step("/analyze", {"criticalities": [{"component": "seal", "value": 3,
          "reason": "Synthetic demo policy value", "set_by": "synthetic"}]})
    assert state["facts"] and state["alerts"]
    assert state["stage_status"]["review"] == "succeeded"
    step("/context", {"asset_id": "PUMP-SYN-01", "component": "seal", "query": "seal leakage flush"})
    assert state["context"]["status"] == "ready"
    pack = state["context"]["pack"]
    assert pack["synthetic"]
    assert "MAN-PUMP-B-v1" not in {p["document_id"] for p in pack["passages"]}
    call("POST", path + "/context", {"expected_revision": state["revision"] - 1,
         "asset_id": "PUMP-SYN-01", "component": "seal", "query": "seal leakage flush"}, 409)
    assert call("GET", path)["revision"] == state["revision"]
    step("/context/generate")
    assert state["draft_result"]["status"] == "pending_expert_review", state["draft_result"]
    assert state["draft_result"]["explanation_mode"] == "hosted_replay"
    call("POST", path + "/reports/issue", {"expected_revision": state["revision"]}, 422)
    step("/expert-review", {"decision": "accepted", "reviewer": "SYNTHETIC DEMO SIGNOFF SIMULATOR",
         "reason": "SIMULATED local E2E signoff; not a real expert decision"})
    assert state["stage_status"]["context"] == "accepted"
    step("/reports/issue")
    report_id = state["latest_report"]["report_id"]
    pdf = call("GET", path + "/report/" + report_id)
    assert pdf.startswith(b"%PDF")
    document = PdfReader(io.BytesIO(pdf))
    text = "\n".join(page.extract_text() or "" for page in document.pages)
    assert "SYNTHETIC DATA" in text and "SIMULATED SIGNOFF" in text
    assert "hosted_replay" in text
    assert "DeepSeek-V4-Flash" in text
    (args.out / "synthetic-replay-report.pdf").write_bytes(pdf)
    (args.out / "report-text.txt").write_text(text, encoding="utf-8")
    (args.out / "run-state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    history = call("GET", path + "/history")
    assert len(history["events"]) >= 15
    result = {"status": "passed", "scope": "HTTP backend workflow using recorded model responses",
              "source_commit": subprocess.check_output(["git", "-C", str(args.project), "rev-parse", "HEAD"], text=True).strip(),
              "synthetic": True, "simulated_signoff": True, "live_model_calls": 0,
              "browser_integration_checked": False,
              "working_tree_modified": bool(subprocess.check_output(["git", "-C", str(args.project), "status", "--porcelain"], text=True).strip()),
              "run_id": run_id, "report_id": report_id,
              "records": len(state["records"]), "approved_records": len(usable),
              "facts": len(state["facts"]), "alerts": len(state["alerts"]),
              "pdf_pages": len(document.pages), "pdf_sha256": hashlib.sha256(pdf).hexdigest(),
              "checks": ["upload and mapping", "recorded extraction", "explicit simulated record review",
                         "code facts and alerts", "wrong-model evidence excluded", "stale revision rejected",
                         "recorded explanation", "report blocked before signoff", "simulated expert signoff",
                         "issued PDF download and source labels", "persisted history"],
              "persistence_verified_after_restart": False}
    persist_result(result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
