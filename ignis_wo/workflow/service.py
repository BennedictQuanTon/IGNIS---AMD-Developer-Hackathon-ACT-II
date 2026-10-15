"""Workflow application service. HTTP handlers stay thin and all state is persisted in SQLite."""
import json
import uuid
import datetime
import base64
from pathlib import Path

from ignis_wo.analytics.explain import build_explanations
from ignis_wo.analytics.facts import compute_facts
from ignis_wo.artifacts import StageFailed
from ignis_wo.contracts import ComponentCriticality, FactRow, Snapshot
from ignis_wo.extraction.adapters import FixtureAdapter, TASK, input_hash
from ignis_wo.extraction.suggest import suggest_all
from ignis_wo.hashing import content_hash
from ignis_wo.hashing import short_id
from ignis_wo.ingest.mapping import build_records, confirm_mapping, propose_mapping
from ignis_wo.ingest.registry import parse_file
from ignis_wo.render.claims import check_claims
from ignis_wo.render.pdf import build_pdf
from ignis_wo.render.templates import build_claims
from ignis_wo.review import apply_decisions
from ignis_wo.snapshot import build_snapshot
from ignis_wo.workflow.alerts import build_alerts
from ignis_wo.workflow.context import retrieve, validate_draft
from ignis_wo.workflow.store import Conflict, NotFound, Store


class WorkflowStageError(RuntimeError):
    def __init__(self, stage: str, message: str, run: dict):
        super().__init__(message)
        self.stage = stage
        self.run = run


class Workflow:
    def __init__(self, db_path: Path, data_dir: Path, fixture_items=None, extraction_provider=None, explanation_provider=None):
        self.store = Store(db_path)
        self.data_dir = data_dir
        self.uploads = data_dir / "uploads"
        self.outputs = data_dir / "outputs"
        self.uploads.mkdir(parents=True, exist_ok=True)
        self.outputs.mkdir(parents=True, exist_ok=True)
        self.fixture_items = fixture_items
        self.extraction_provider = extraction_provider
        self.explanation_provider = explanation_provider

    def create_run(self, name: str, operator: str, synthetic: bool, adapter_mode: str = "unavailable"):
        if not name.strip() or not operator.strip():
            raise ValueError("run name and local operator are required")
        if adapter_mode not in {"unavailable", "fixture", "injected"}:
            raise ValueError("adapter_mode must be unavailable, fixture or injected")
        if adapter_mode == "fixture" and not self.fixture_items:
            raise ValueError("fixture corpus is not configured")
        if adapter_mode == "injected" and not self.extraction_provider:
            raise ValueError("injected mode requires an extraction_provider interface")
        run_id = "R-" + uuid.uuid4().hex[:16]
        upload_path = self.uploads / f"{run_id}.csv"
        return self.store.create(run_id, {"name": name, "operator": operator, "synthetic": bool(synthetic), "adapter_mode": adapter_mode,
            "upload_path": str(upload_path), "mapping": None, "records": [], "suggestions": [], "decisions": {}, "snapshot": None,
            "facts": [], "alerts": [], "context": None, "expert_reviews": [], "report_ids": [], "stage_status": {"upload": "pending"}})

    def get(self, run_id):
        return self.store.get(run_id)

    def upload(self, run_id, revision, filename, csv_text=None, content_base64=None):
        run = self.get(run_id)
        if run["revision"] != revision:
            raise Conflict(f"expected revision {revision}; current revision is {run['revision']}")
        suffix = Path(filename).suffix.lower()
        if suffix not in {".csv", ".tsv", ".json", ".jsonl", ".xlsx"}:
            raise ValueError("supported source files: CSV, TSV, JSON, JSONL and XLSX")
        path = self.uploads / f"{run_id}-{uuid.uuid4().hex[:8]}{suffix}"
        if not csv_text and not content_base64:
            raise ValueError("source file is empty")
        try:
            path.write_bytes(base64.b64decode(content_base64, validate=True) if content_base64 else csv_text.encode("utf-8"))
        except Exception as error:
            raise ValueError(f"invalid base64 source content: {error}") from error
        try:
            try:
                source, rows = parse_file(path)
                proposal = propose_mapping(sorted({c for row in rows for c in row.values}))
            except Exception as error:
                path.unlink(missing_ok=True)
                message = f"{type(error).__name__}: {error}"
                failed = self.store.mutate(run_id, revision, "upload_parse_failed", {
                    "latest_report": None,
                    "stage_status": {**run["stage_status"], "upload": "failed", "report": "pending"},
                    "stage_errors": [*run.get("stage_errors", []), f"upload: {message}"],
                }, "degraded")
                raise WorkflowStageError("upload", message, failed) from error
            return self.store.mutate(run_id, revision, "source_uploaded", {"upload_path": str(path), "filename": filename, "source_sha256": source.sha256,
                "row_count": len(rows), "columns": sorted({c for row in rows for c in row.values}), "proposal": proposal.model_dump(mode="json"),
                "raw_rows": [row.model_dump(mode="json") for row in rows],
                "mapping": None, "records": [], "suggestions": [], "decisions": {}, "snapshot": None, "facts": [], "alerts": [], "context": None,
                "last_snapshot": run.get("snapshot") or run.get("last_snapshot"), "last_facts": run.get("facts") or run.get("last_facts", []),
                "draft_result": None, "expert_reviews": [], "latest_report": None,
                "stage_errors": [],
                "stage_status": {"upload": "succeeded", "mapping": "pending", "extraction": "pending", "review": "pending", "facts": "pending", "alerts": "pending", "context": "pending", "report": "pending"}}, "uploaded")
        except Exception:
            path.unlink(missing_ok=True)
            raise

    def confirm_mapping(self, run_id, revision, mapping, reason):
        run = self.get(run_id)
        if not reason or not reason.strip():
            raise ValueError("mapping confirmation reason is required")
        available = set(run["columns"])
        unknown = sorted(value for value in mapping.values() if value is not None and value not in available)
        if unknown:
            raise ValueError(f"mapping references unknown source column(s): {', '.join(unknown)}")
        source, rows = parse_file(Path(run["upload_path"]))
        proposal = propose_mapping(run["columns"])
        confirmed = confirm_mapping(proposal, run["operator"], reason, mapping)
        records, issues = build_records(source, rows, confirmed)
        if not records:
            raise ValueError("mapping produced no usable records: " + "; ".join(issues))
        # Confirmed remaps invalidate all downstream data, even if column names happen to match.
        return self.store.mutate(run_id, revision, "mapping_confirmed", {"mapping": confirmed.model_dump(mode="json"),
            "records": [r.model_dump(mode="json") for r in records], "row_issues": issues,
            "suggestions": [], "decisions": {}, "snapshot": None, "facts": [], "alerts": [], "context": None, "draft_result": None, "expert_reviews": [], "latest_report": None,
            "last_snapshot": run.get("snapshot") or run.get("last_snapshot"), "last_facts": run.get("facts") or run.get("last_facts", []),
            "stage_status": {"upload": "succeeded", "mapping": "succeeded", "extraction": "pending", "review": "pending", "facts": "pending", "alerts": "pending", "context": "pending", "report": "pending"}}, "mapped")

    def extract(self, run_id, revision):
        run = self.get(run_id)
        if run["revision"] != revision:
            raise Conflict(f"expected revision {revision}; current revision is {run['revision']}")
        if run["suggestions"]:
            return run
        if not run["mapping"]:
            raise ValueError("confirm a source mapping before extraction")
        if run["adapter_mode"] == "unavailable":
            return self.store.mutate(run_id, revision, "extraction_unavailable", {"stage_status": {**run["stage_status"], "extraction": "unavailable"},
                "stage_errors": ["No extraction provider configured; fixture, replay or hosted adapter must be explicitly configured."]}, "degraded")
        from ignis_wo.contracts import CanonicalRecord
        records = [CanonicalRecord.model_validate(r) for r in run["records"]]
        try:
            if run["adapter_mode"] == "injected":
                suggestions = self.extraction_provider(records)
            else:
                suggestions = suggest_all(records, FixtureAdapter(self.fixture_items, model_version="maintie-gold-demo"))
        except Exception as error:
            return self.store.mutate(run_id, revision, "extraction_failed", {"stage_status": {**run["stage_status"], "extraction": "failed"}, "stage_errors": [f"{type(error).__name__}: {error}"]}, "degraded")
        return self.store.mutate(run_id, revision, "suggestions_saved", {"suggestions": [s.model_dump(mode="json") for s in suggestions],
            "stage_status": {**run["stage_status"], "extraction": "succeeded", "review": "pending"}, "stage_errors": []}, "review_pending")

    def review(self, run_id, revision, record_id, status, reason, correction=None, reviewer=None, demo_auto_review=False):
        run = self.get(run_id)
        decisions = dict(run["decisions"])
        if record_id not in {r["record_id"] for r in run["records"]}:
            raise ValueError("record_id does not belong to this run")
        if status not in {"accepted", "corrected", "rejected"} or not reason or not reason.strip() or (reviewer is not None and (not isinstance(reviewer, str) or not reviewer.strip())):
            raise ValueError("decision must be accepted, corrected or rejected, with a reason")
        reviewer = reviewer or run["operator"]
        if demo_auto_review:
            if run["adapter_mode"] != "fixture" or not run["synthetic"]:
                raise ValueError("demo auto-review requires synthetic fixture mode")
            reviewer = "AUTOMATIC SYNTHETIC FIXTURE DEMO (not a human reviewer)"
            reason = "AUTOMATIC SYNTHETIC FIXTURE DEMO (not a human decision): " + reason
        previous = decisions.get(record_id, {})
        decision = {"record_id": record_id, "status": status, "reason": reason, "output": correction,
                                "reviewer": reviewer, "reviewed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "revision": previous.get("revision", 0) + 1}
        from ignis_wo.contracts import CanonicalRecord, ExtractionSuggestion
        target = next((s for s in run["suggestions"] if s["record_id"] == record_id), None)
        suggestion_rows = list(run["suggestions"])
        if target is None:
            if status != "corrected":
                raise ValueError("without a provider suggestion, a manual corrected annotation is required")
            record = next(r for r in run["records"] if r["record_id"] == record_id)
            target = ExtractionSuggestion(suggestion_id=short_id("sug", record_id, "manual", str(decision["revision"])), record_id=record_id,
                adapter_mode="manual", model_id="manual-entry", model_version="1", task=TASK, input_hash=input_hash(record["text_norm"]),
                status="needs_review", output=None, errors=["No extraction provider configured; manually corrected by reviewer."])
            suggestion_rows.append(target.model_dump(mode="json"))
        apply_decisions([ExtractionSuggestion.model_validate(target)], [CanonicalRecord.model_validate(r) for r in run["records"]], {record_id: decision}, reviewer)
        decisions[record_id] = decision
        updated = self.store.mutate(run_id, revision, "record_reviewed", {"decisions": decisions,
            "suggestions": suggestion_rows,
            "last_snapshot": run.get("snapshot") or run.get("last_snapshot"), "last_facts": run.get("facts") or run.get("last_facts", []),
            "snapshot": None, "facts": [], "alerts": [], "context": None, "draft_result": None, "expert_reviews": [], "latest_report": None,
            "stage_status": {**run["stage_status"], "review": "pending", "facts": "pending", "alerts": "pending", "context": "pending", "report": "pending"}}, "review_pending")
        return updated

    def analyze(self, run_id, revision, criticalities=None):
        run = self.get(run_id)
        if not run["suggestions"]:
            raise ValueError("extraction suggestions are required before review")
        from ignis_wo.contracts import CanonicalRecord, ExtractionSuggestion
        records = [CanonicalRecord.model_validate(r) for r in run["records"]]
        suggestions = [ExtractionSuggestion.model_validate(s) for s in run["suggestions"]]
        decisions = {d["record_id"]: d for d in run["decisions"].values()}
        annotations = apply_decisions(suggestions, records, decisions, run["operator"])
        snapshot = build_snapshot(records, annotations, [ComponentCriticality.model_validate(c) for c in (criticalities or [])], {"facts": "facts-v1", "severity": "severity-v1", "triage": "triage-v1"})
        if not snapshot.entries:
            raise ValueError("no accepted or corrected records; pending/rejected records are excluded")
        assets = {e.record.asset_id for e in snapshot.entries if e.record.asset_id}
        if len(assets) > 1 or (assets and any(entry.record.asset_id is None for entry in snapshot.entries)):
            raise ValueError("this bounded demo cannot mix asset identities or records missing an asset with known-asset records")
        facts = compute_facts(snapshot)
        prior_data = run.get("snapshot") or run.get("last_snapshot")
        prior_fact_data = run.get("facts") or run.get("last_facts", [])
        prior_snapshot = Snapshot.model_validate(prior_data) if prior_data else None
        prior_facts = [FactRow.model_validate(f) for f in prior_fact_data]
        if prior_snapshot:
            prior_assets = {entry.record.asset_id for entry in prior_snapshot.entries}
            current_assets = {entry.record.asset_id for entry in snapshot.entries}
            if prior_assets != current_assets:
                # Asset identity is a hard comparison boundary. A new asset starts a fresh baseline.
                prior_snapshot = None
                prior_facts = []
        alerts = build_alerts(snapshot, facts, prior_snapshot, prior_facts)
        if prior_snapshot and prior_snapshot.snapshot_id == snapshot.snapshot_id:
            alerts = run["alerts"]
        explanations = build_explanations(snapshot, facts, run["adapter_mode"], run["synthetic"])
        changed_snapshot = not prior_snapshot or prior_snapshot.snapshot_id != snapshot.snapshot_id
        downstream = {"context": None, "draft_result": None, "expert_reviews": [], "latest_report": None,
                      "stage_status": {**run["stage_status"], "facts": "succeeded", "alerts": "succeeded", "context": "pending", "report": "pending"}} if changed_snapshot else {}
        return self.store.mutate(run_id, revision, "analysis_completed", {"last_snapshot": snapshot.model_dump(mode="json"), "last_facts": [f.model_dump(mode="json") for f in facts], "snapshot": snapshot.model_dump(mode="json"),
            "facts": [f.model_dump(mode="json") for f in facts], "alerts": alerts,
            "explanations": [e.model_dump(mode="json") for e in explanations], "stage_status": {**run["stage_status"], "review": "succeeded", "facts": "succeeded", "alerts": "succeeded"},
            "criticalities": [c.model_dump(mode="json") for c in [ComponentCriticality.model_validate(x) for x in (criticalities or [])]], **downstream}, "analyzed")

    def build_context(self, run_id, revision, asset_id, component, query):
        run = self.get(run_id)
        if not run["snapshot"]:
            raise ValueError("an approved snapshot is required before context retrieval")
        snapshot = Snapshot.model_validate(run["snapshot"])
        snapshot_assets = {entry.record.asset_id for entry in snapshot.entries}
        if not asset_id or snapshot_assets != {asset_id}:
            result = {"status": "insufficient_applicability", "reason": "requested asset identity must exactly match the single approved snapshot asset", "trace": {"eligible_ids": [], "excluded": [], "paths": []}, "pack": None}
        else:
            result = retrieve(asset_id, component, query, run["facts"], run["snapshot"]["snapshot_id"])
        def persist_pack(db, _revision):
            if result["pack"]:
                db.execute("INSERT OR IGNORE INTO packs VALUES (?,?,?)", (result["pack"]["pack_id"], run_id, json.dumps(result["pack"])))
        return self.store.mutate(run_id, revision, "context_retrieved", {"context": result, "draft_result": None, "expert_reviews": [], "latest_report": None,
            "stage_status": {**run["stage_status"], "context": result["status"], "report": "pending"}}, "context_ready" if result["status"] == "ready" else "context_unavailable", before_commit=persist_pack)

    def submit_draft(self, run_id, revision, draft):
        run = self.get(run_id)
        context = run["context"] or {}
        pack = context.get("pack")
        errors = ["context pack is unavailable"] if not pack else validate_draft(pack, draft)
        result = {"status": "invalid" if errors else "pending_expert_review", "errors": errors, "draft": draft if not errors else None,
            "pack_id": pack["pack_id"] if pack else None, "explanation_mode": "manual"}
        return self.store.mutate(run_id, revision, "context_draft_validated", {"draft_result": result,
            "stage_status": {**run["stage_status"], "context": "invalid" if errors else "pending_expert_review", "report": "pending"}}, "draft_invalid" if errors else "draft_pending_review")

    def generate_context_draft(self, run_id, revision):
        run = self.get(run_id)
        if run["revision"] != revision:
            raise Conflict(f"expected revision {revision}; current revision is {run['revision']}")
        pack = (run.get("context") or {}).get("pack")
        if not pack:
            result = {"status": "unavailable", "errors": ["evidence pack unavailable"], "draft": None, "pack_id": None, "explanation_mode": "unavailable"}
            return self.store.mutate(run_id, revision, "context_generation_unavailable", {"draft_result": result,
                "stage_status": {**run["stage_status"], "context": "unavailable", "report": "pending"}}, "context_unavailable")
        if not self.explanation_provider:
            result = {"status": "unavailable", "errors": ["No hosted explanation provider is configured in this delivery."], "draft": None, "pack_id": pack["pack_id"], "explanation_mode": "unavailable"}
            return self.store.mutate(run_id, revision, "context_generation_unavailable", {"draft_result": result,
                "stage_status": {**run["stage_status"], "context": "unavailable", "report": "pending"}}, "context_unavailable")
        try:
            draft = self.explanation_provider(pack)
        except Exception as error:
            draft = None
            errors = [f"{type(error).__name__}: {error}"]
        else:
            errors = validate_draft(pack, draft)
        result = {"status": "invalid" if errors else "pending_expert_review", "errors": errors, "draft": draft if not errors else None,
                  "pack_id": pack["pack_id"], "explanation_mode": getattr(self.explanation_provider, "explanation_mode", "injected"), "model_id": getattr(self.explanation_provider, "model_id", "injected"), "prompt_id": getattr(self.explanation_provider, "prompt_id", "injected-prompt")}
        return self.store.mutate(run_id, revision, "context_generation_completed", {"draft_result": result,
            "stage_status": {**run["stage_status"], "context": "invalid" if errors else "pending_expert_review", "report": "pending"}}, "draft_invalid" if errors else "draft_pending_review")

    def expert_review(self, run_id, revision, decision, reviewer, reason, corrected=None):
        run = self.get(run_id)
        allowed = {"accepted", "corrected", "rejected", "inconclusive", "facts_only_approved"}
        if decision not in allowed or not reviewer or not reviewer.strip() or not reason or not reason.strip():
            raise ValueError("expert decision, reviewer and reason are required")
        if decision == "facts_only_approved":
            context_status = (run.get("context") or {}).get("status")
            draft_status = (run.get("draft_result") or {}).get("status")
            if context_status not in {"context_unavailable", "insufficient_applicability"} and draft_status not in {"invalid", "unavailable"}:
                raise ValueError("facts-only approval requires unavailable/insufficient context or an invalid draft")
        elif not run.get("draft_result") or run["draft_result"]["status"] != "pending_expert_review":
            raise ValueError("a valid pending draft is required")
        review = {"decision": decision, "reviewer": reviewer, "reason": reason, "corrected": corrected, "revision": len(run["expert_reviews"]) + 1}
        review.update({"reviewed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "snapshot_id": run["snapshot"]["snapshot_id"],
                       "pack_id": (run.get("draft_result") or {}).get("pack_id"), "draft_hash": content_hash(run["draft_result"]["draft"]) if (run.get("draft_result") or {}).get("draft") else None})
        if decision == "corrected":
            pack = (run.get("context") or {}).get("pack")
            errors = validate_draft(pack, corrected) if pack else ["evidence pack is unavailable"]
            if errors:
                raise ValueError("expert correction is invalid: " + "; ".join(errors))
            review["corrected_hash"] = content_hash(corrected)
        return self.store.mutate(run_id, revision, "expert_reviewed", {"expert_reviews": run["expert_reviews"] + [review],
            "stage_status": {**run["stage_status"], "report": "pending"}}, "expert_reviewed")

    def issue_report(self, run_id, revision):
        run = self.get(run_id)
        if not run["snapshot"]:
            raise ValueError("analyzed approved snapshot is required")
        review = run["expert_reviews"][-1] if run["expert_reviews"] else None
        if not review or review["decision"] not in {"accepted", "corrected", "facts_only_approved"} or review["snapshot_id"] != run["snapshot"]["snapshot_id"]:
            raise ValueError("current-snapshot expert signoff is required before report issue")
        if review["decision"] != "facts_only_approved":
            if not run.get("draft_result") or review["pack_id"] != run["draft_result"]["pack_id"] or review["draft_hash"] != content_hash(run["draft_result"]["draft"]):
                raise ValueError("expert signoff does not match the current pack and draft")
        simulated_signoff = "SIMULATOR" in review["reviewer"].upper() or "SYNTHETIC DEMO" in review["reviewer"].upper()
        snapshot = Snapshot.model_validate(run["snapshot"])
        facts = [FactRow.model_validate(f) for f in run["facts"]]
        from ignis_wo.contracts import ComponentExplanation
        explanations = [ComponentExplanation.model_validate(e) for e in run["explanations"]]
        claims = build_claims(snapshot, facts, explanations)
        failures = check_claims(claims, facts, snapshot.snapshot_id)
        if failures:
            raise ValueError(f"report claim validation failed: {failures}")
        report_id = "REP-" + uuid.uuid4().hex[:14]
        out_dir = self.outputs / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{report_id}.pdf"
        from ignis_wo.hashing import sha256_bytes
        payload = {"report_id": report_id, "status": "issued", "path": str(path), "sha256": None, "snapshot_id": snapshot.snapshot_id,
            "run_id": run_id, "expert_review": review, "pack_id": review.get("pack_id"), "synthetic": run["synthetic"], "adapter_mode": run["adapter_mode"], "prompt_id": (run.get("draft_result") or {}).get("prompt_id", "N/A: no hosted explanation provider configured")}
        def record_report(db, _next_revision):
            try:
                build_pdf(path, snapshot, facts, explanations, claims, {"data_label": ("SYNTHETIC DATA" if run["synthetic"] else "SOURCE DATA") + (" / SIMULATED SIGNOFF" if simulated_signoff else " / EXPERT REVIEWED"),
                "adapter_mode": run["adapter_mode"], "explanation_mode": (run.get("draft_result") or {}).get("explanation_mode", "unavailable"), "model_id": "fixture-gold" if run["adapter_mode"] == "fixture" else "unavailable",
                "model_version": "maintie-gold-demo" if run["adapter_mode"] == "fixture" else "none", "source_name": run.get("filename", "unknown"),
                "source_sha256": run.get("source_sha256", "unknown"), "mapping_revision": run["mapping"]["revision_id"], "reviewer": run["operator"],
                "data_basis": [f"Approved snapshot {snapshot.snapshot_id}; {len(snapshot.entries)} records.", "Synthetic pump fields and corpus are labeled synthetic.",
                    "AUTOMATIC SYNTHETIC FIXTURE DECISIONS are not human review." if any("AUTOMATIC SYNTHETIC FIXTURE DEMO" in d.get("reviewer", "") for d in run["decisions"].values()) else "Record decisions are attributed in the persisted review history." ]},
                context_review={"decision": review["decision"], "snapshot_id": review["snapshot_id"], "pack_id": review.get("pack_id"),
                    "review_status": review["decision"] + (" (simulated; not a real expert decision)" if simulated_signoff else ""),
                    "explanation_mode": (run.get("draft_result") or {}).get("explanation_mode", "unavailable"), "prompt_id": (run.get("draft_result") or {}).get("prompt_id", "N/A: hosted explanation provider unavailable in this delivery"),
                    "model_id": (run.get("draft_result") or {}).get("model_id", "unavailable"),
                    "approved_draft": review.get("corrected") if review["decision"] == "corrected" else ((run.get("draft_result") or {}).get("draft") if review["decision"] == "accepted" else None),
                    "draft_hash": review.get("corrected_hash", review.get("draft_hash")), "reviewer": review["reviewer"], "reviewed_at": review["reviewed_at"], "revision": review["revision"], "reason": review["reason"]})
            except Exception as error:
                render_errors.append(error)
                raise
            payload["sha256"] = sha256_bytes(path.read_bytes())
            db.execute("INSERT INTO reports VALUES (?,?,?,?)", (report_id, run_id, "issued", json.dumps(payload)))
        render_errors = []
        try:
            return self.store.mutate(run_id, revision, "report_issued", {"report_ids": run["report_ids"] + [report_id], "latest_report": payload,
                "stage_status": {**run["stage_status"], "report": "succeeded"},
                "stage_errors": [error for error in run.get("stage_errors", []) if not error.startswith("report:")]}, "report_issued", before_commit=record_report)
        except Exception as error:
            path.unlink(missing_ok=True)
            if render_errors:
                message = f"{type(error).__name__}: {error}"
                failed = self.store.mutate(run_id, revision, "report_render_failed", {
                    "latest_report": None,
                    "stage_status": {**run["stage_status"], "report": "failed"},
                    "stage_errors": [*run.get("stage_errors", []), f"report: {message}"],
                }, "degraded")
                raise WorkflowStageError("report", message, failed) from error
            raise
