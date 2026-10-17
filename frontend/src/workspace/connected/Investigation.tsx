import { useState } from "react";
import { Badge } from "../../components/ui/primitives";
import type { Controller } from "./ConnectedWorkspace";
import { reportUrl, request, type Claim, type Run } from "./api";
import { canIssue } from "./workflow";
import { Button, Field, inputClass, JsonView, Note, Panel } from "./ui";

type Props = { w: Controller; inspect: (id: string) => void };
function Ref({ id, inspect }: { id: string; inspect: (id: string) => void }) { return <button type="button" className="rounded border border-line-strong px-2 py-1 font-mono text-xs text-info hover:bg-hover" onClick={() => inspect(id)}>{id}</button>; }

export function FactsStage({ w, next, simulation, inspect }: Props & { next: () => void; simulation: boolean }) {
  const run = w.run!;
  const [component, setComponent] = useState(run.criticalities?.[0]?.component || "seal");
  const [value, setValue] = useState(run.criticalities?.[0]?.value || 3);
  const [reason, setReason] = useState(run.criticalities?.[0]?.reason || "Supervisor criticality policy for this review");
  const disabled = !!w.busy || w.cooldown > 0;
  const decided = Object.keys(run.decisions).length;
  return <div className="space-y-4"><Panel title="Compute facts and alerts">
    <Note>{decided} of {run.records.length} records decided. Pending and rejected records are excluded from the approved snapshot. Priority is a rule-based historical ordering, not a failure probability.</Note>
    <fieldset disabled={disabled} className="space-y-3"><div className="grid gap-3 sm:grid-cols-3"><Field label="Critical component"><input className={inputClass} value={component} onChange={event => setComponent(event.target.value)} /></Field>
      <Field label="Criticality multiplier"><input type="number" min={1} step={1} className={inputClass} value={value} onChange={event => setValue(Number(event.target.value))} /></Field>
      <Field label="Criticality reason"><input className={inputClass} value={simulation ? "Synthetic demo policy value" : reason} disabled={simulation} onChange={event => setReason(event.target.value)} /></Field></div>
      <Button primary disabled={!run.suggestions.length || !component.trim() || !Number.isInteger(value) || value < 1 || !reason.trim()} onClick={() => void w.mutate("/analyze", { criticalities: [{ component, value, reason: simulation ? "Synthetic demo policy value" : reason, set_by: simulation ? "synthetic" : run.operator }] }, "Computing facts and alerts")}>Analyze approved records</Button>
      <Button disabled={!run.snapshot} onClick={next}>Continue to evidence</Button>
    </fieldset>
    {run.snapshot && <Note>Snapshot {run.snapshot.snapshot_id} · {run.snapshot.entries.length} approved records</Note>}
  </Panel>
    <Panel title="Backend facts"><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr>{["Fact", "Scope", "Value", "Status", "Source records"].map(label => <th key={label} className="p-2">{label}</th>)}</tr></thead><tbody>{run.facts.map(fact => <tr key={fact.fact_id} className="border-t border-line align-top"><td className="p-2"><Ref id={fact.fact_id} inspect={inspect} /><p className="mt-1 text-xs text-fg-3">{fact.kind}</p></td><td className="p-2">{Object.entries(fact.scope).map(([key, scope]) => <p key={key}>{key}: {scope}</p>)}</td><td className="p-2">{fact.status === "computed" ? `${fact.value} ${fact.unit}` : "Not computed"}</td><td className="p-2">{fact.status}<p className="text-xs text-fg-3">{fact.reason}</p></td><td className="p-2"><div className="flex flex-wrap gap-1">{fact.record_ids.map(id => <Ref key={id} id={id} inspect={inspect} />)}</div></td></tr>)}</tbody></table></div></Panel>
    <Panel title="Deterministic alerts">{run.alerts.length ? run.alerts.map((alert, index) => <JsonView key={index} value={alert} />) : <Note>No alerts in the current saved run.</Note>}</Panel>
  </div>;
}

function ClaimView({ claim, inspect }: { claim: Claim; inspect: (id: string) => void }) {
  return <div className="space-y-2 rounded-lg border border-line p-3"><p>{claim.text}</p><div className="flex flex-wrap gap-2">{claim.citations.map(id => <Ref key={id} id={id} inspect={inspect} />)}</div>
    {!!claim.fact_bindings.length && <details><summary className="cursor-pointer text-xs text-fg-3">Typed numeric fact bindings</summary><JsonView value={claim.fact_bindings} /></details>}</div>;
}

export function EvidenceStage({ w, next, inspect, allowLive }: Props & { next: () => void; allowLive: boolean }) {
  const run = w.run!;
  const [asset, setAsset] = useState(run.records.find(record => record.asset_id)?.asset_id || "PUMP-SYN-01");
  const [component, setComponent] = useState("seal");
  const [query, setQuery] = useState("seal leakage flush");
  const [outcome, setOutcome] = useState("accepted");
  const [reason, setReason] = useState("");
  const [reviewer, setReviewer] = useState(run.operator);
  const [simulated, setSimulated] = useState(run.synthetic);
  const [corrected, setCorrected] = useState("");
  const [manualDraft, setManualDraft] = useState("");
  const disabled = !!w.busy || w.cooldown > 0;
  const pack = run.context?.pack;
  const result = run.draft_result;
  const draft = result?.draft;
  const factsOnly = ["context_unavailable", "insufficient_applicability"].includes(run.context?.status || "") || ["invalid", "unavailable"].includes(result?.status || "");
  const pendingDraft = result?.status === "pending_expert_review";
  return <div className="space-y-4"><Panel title="Retrieve applicable evidence">
    <Note>Rebuilding context clears the draft and expert signoff. Existing facts and historical PDFs remain available.</Note>
    <fieldset disabled={disabled} className="space-y-3"><div className="grid gap-3 sm:grid-cols-3"><Field label="Evidence asset"><input className={inputClass} value={asset} onChange={event => setAsset(event.target.value)} /></Field><Field label="Evidence component"><input className={inputClass} value={component} onChange={event => setComponent(event.target.value)} /></Field><Field label="Evidence query"><input className={inputClass} value={query} onChange={event => setQuery(event.target.value)} /></Field></div>
      <Button primary disabled={!run.snapshot || !asset.trim() || !component.trim()} onClick={() => void w.mutate("/context", { asset_id: asset, component, query }, "Retrieving scoped evidence")}>Retrieve evidence</Button>
    </fieldset>
    {run.context && <><Badge t={run.context.status === "ready" ? "ok" : "warn"}>{run.context.status}</Badge><Note>{run.context.reason}</Note><Note>{run.context.corpus_mode} · {pack?.corpus_version} · {pack?.pack_id}</Note><details><summary className="cursor-pointer">Applicability paths and excluded sources</summary><JsonView value={run.context.trace} /></details></>}
    {pack?.passages.map(passage => <article key={passage.passage_id} className="space-y-2 rounded-lg border border-line p-3"><Ref id={passage.passage_id} inspect={inspect} /><Note>{passage.document_id} · revision {passage.version} · {passage.location}</Note><p className="whitespace-pre-wrap">{passage.text}</p></article>)}
  </Panel>
    <Panel title="Explanation proposal">
      <Button primary disabled={disabled || !pack || (w.health?.explanation_mode === "hosted_live" && !allowLive)} onClick={() => void w.mutate("/context/generate", {}, "Generating cited explanation")}>Generate explanation</Button>
      <Note>Replay only matches the recorded evidence pack. Changed reviews, criticality or query can miss the recording; that is shown as an error, never replaced by a live call.</Note>
      {result && <><Badge t={result.status === "invalid" ? "danger" : "info"}>Draft: {result.status === "pending_expert_review" ? "validated" : result.status}</Badge><Badge>Expert review: {run.expert_reviews.at(-1)?.decision || "pending"}</Badge><Note>{result.explanation_mode} · {result.model_id} · {result.prompt_id}</Note>{!!result.errors.length && <div role="note" className="text-sm text-danger">{result.errors.join("; ")}</div>}</>}
      {draft && <><h3 className="font-semibold">{draft.abstain ? "Abstention" : "Hypotheses — not confirmed causes"}</h3>{draft.hypotheses.map((claim, index) => <ClaimView key={index} claim={claim} inspect={inspect} />)}<h3 className="font-semibold">Alternatives</h3>{draft.alternatives.map((claim, index) => <ClaimView key={index} claim={claim} inspect={inspect} />)}<Note>{draft.uncertainty}</Note>{draft.inspection && <ClaimView claim={draft.inspection} inspect={inspect} />}</>}
      {pack && <details><summary className="cursor-pointer text-sm">Enter a manually authored cited draft</summary><Field label="Manual cited draft JSON"><textarea rows={10} className={inputClass + " font-mono text-xs"} value={manualDraft} onChange={event => setManualDraft(event.target.value)} /></Field><Button disabled={disabled || !manualDraft.trim()} onClick={() => void w.perform("Validating manual draft", async () => {
        let value; try { value = JSON.parse(manualDraft); } catch { throw new Error("Manual draft must be valid JSON."); }
        await w.select(await request<Run>(`/runs/${run.run_id}/context/draft`, { expected_revision: run.revision, draft: value }));
      })}>Validate and save manual draft</Button><Note>Use the current pack_id, typed claim objects and citations from the inspector. This path is labelled manual.</Note></details>}
    </Panel>
    <Panel title="Explicit expert review">
      <Note>Review accepts a finding for this snapshot; it does not authorize maintenance work. Rejected and inconclusive decisions cannot issue a report.</Note>
      <fieldset disabled={disabled} className="space-y-3"><Field label="Expert decision"><select className={inputClass} value={outcome} onChange={event => setOutcome(event.target.value)}><option value="accepted">Accept finding</option><option value="corrected">Correct finding</option><option value="rejected">Reject finding</option><option value="inconclusive">Inconclusive</option><option value="facts_only_approved" disabled={!factsOnly}>Approve facts only (unavailable/invalid context)</option></select></Field>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={simulated} onChange={event => setSimulated(event.target.checked)} />Simulated demonstration signoff (not a real expert decision)</label>
        <Field label="Expert reviewer"><input className={inputClass} value={simulated ? "SYNTHETIC DEMO SIGNOFF SIMULATOR" : reviewer} disabled={simulated} onChange={event => setReviewer(event.target.value)} /></Field>
        <Field label="Expert review reason"><textarea className={inputClass} value={reason} onChange={event => setReason(event.target.value)} /></Field>
        {outcome === "corrected" && <Field label="Corrected cited draft JSON"><textarea rows={12} className={inputClass + " font-mono text-xs"} value={corrected || JSON.stringify(draft, null, 2)} onChange={event => setCorrected(event.target.value)} /></Field>}
        <Button primary disabled={!reason.trim() || (!simulated && !reviewer.trim()) || (outcome === "facts_only_approved" ? !factsOnly : !pendingDraft)} onClick={() => void w.perform("Saving expert review", async () => {
          let correction; if (outcome === "corrected") { try { correction = JSON.parse(corrected || JSON.stringify(draft)); } catch { throw new Error("Corrected draft must be valid JSON."); } }
          await w.select(await request<Run>(`/runs/${run.run_id}/expert-review`, { expected_revision: run.revision, decision: outcome,
            reviewer: simulated ? "SYNTHETIC DEMO SIGNOFF SIMULATOR" : reviewer, reason: simulated ? `SIMULATED: ${reason}` : reason, ...(correction ? { corrected: correction } : {}) }));
        })}>Save expert review</Button><Button onClick={next}>Continue to report</Button>
      </fieldset>
      {!!run.expert_reviews.length && <JsonView value={run.expert_reviews.at(-1)} />}
    </Panel>
  </div>;
}

export function ReportStage({ w, inspect }: Props) {
  const run = w.run!;
  const disabled = !!w.busy || w.cooldown > 0;
  return <div className="space-y-4"><Panel title="Issue an evidence-linked report">
    <Note>The backend rechecks the exact snapshot, evidence pack and draft signoff before issuing. A previous PDF is never presented as a new successful render.</Note>
    <Button primary disabled={disabled || !canIssue(run)} onClick={() => void w.mutate("/reports/issue", {}, "Rendering approved report")}>Issue approved PDF</Button>
    {!canIssue(run) && <Note>Current snapshot signoff is required. Rejected or inconclusive decisions block issuance.</Note>}
    {run.latest_report ? <div className="space-y-3"><Badge t="ok">Current issued report</Badge><a className="inline-block rounded-lg border border-accent px-4 py-2 text-brand-text" href={reportUrl(run.run_id, run.latest_report.report_id)} download={`${run.latest_report.report_id}.pdf`}>Download current PDF</a><JsonView value={run.latest_report} /></div> : <Note>No current issued PDF. Historical versions below remain tied to their original snapshots.</Note>}
    <div className="flex flex-wrap gap-2">{run.facts.map(fact => <Ref key={fact.fact_id} id={fact.fact_id} inspect={inspect} />)}</div>
  </Panel><Panel title="Issued report history">
    {w.reports.map(report => <div key={report.report_id} className="space-y-2 rounded-lg border border-line p-3"><Badge>{report.report_id === run.latest_report?.report_id ? "Current version" : "Historical version"}</Badge><p className="break-all font-mono text-xs">{report.report_id} · {report.snapshot_id}</p><a className="text-info underline" href={reportUrl(run.run_id, report.report_id)} download={`${report.report_id}.pdf`}>Download {report.report_id === run.latest_report?.report_id ? "issued" : "historical"} PDF</a><details><summary className="cursor-pointer text-sm">Provenance and signoff</summary><JsonView value={report} /></details></div>)}
    {!w.reports.length && <Note>No issued reports in saved history.</Note>}
  </Panel></div>;
}
