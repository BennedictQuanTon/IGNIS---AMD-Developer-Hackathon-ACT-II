import { useState } from "react";
import { Badge } from "../../components/ui/primitives";
import type { Controller } from "./ConnectedWorkspace";
import { request, type RecordRow, type Run, type Suggestion } from "./api";
import { Button, Field, inputClass, JsonView, Note, Panel } from "./ui";

export function ReviewStage({ w, next, simulation, setSimulation, inspect, allowLive }: { w: Controller; next: () => void; simulation: boolean; setSimulation: (value: boolean) => void; inspect: (id: string) => void; allowLive: boolean }) {
  const run = w.run!;
  const disabled = !!w.busy || w.cooldown > 0;
  const liveBlocked = w.health?.extraction_mode === "hosted_live" && !allowLive;
  if (!run.mapping) return <Note>Confirm the column mapping first.</Note>;
  return <div className="space-y-4"><Panel title="Extraction and record decisions">
    <Note>Model proposals remain unapproved until you decide. Invalid proposals can be corrected manually or rejected; they cannot be accepted.</Note>
    <div className="flex flex-wrap items-center gap-3"><Badge>Extraction: {run.stage_status.extraction}</Badge><Badge>Review: {run.stage_status.review}</Badge>
      <Button primary disabled={disabled || liveBlocked || !!run.suggestions.length} onClick={() => void w.mutate("/extraction/start", {}, "Extracting record proposals")}>Start extraction</Button>
      <Button onClick={next}>Continue to facts</Button>
    </div>
    {liveBlocked && <Note>Enable live calls in the header before requesting live inference.</Note>}
    {run.extraction_identity && <JsonView value={run.extraction_identity} />}
    {w.health?.extraction_mode === "hosted_replay" && run.synthetic && <label className="flex items-start gap-2 text-sm text-synthetic"><input type="checkbox" checked={simulation} onChange={event => setSimulation(event.target.checked)} />Use recorded-demo decisions (simulated attribution; required to reproduce the recorded explanation). Turn off for your own review.</label>}
  </Panel>
    {run.records.map(record => <RecordDecision key={`${record.record_id}:${run.stage_status.extraction}:${run.decisions[record.record_id]?.revision || 0}:${simulation}`} w={w} record={record}
      suggestion={run.suggestions.find(value => value.record_id === record.record_id)} simulation={simulation && w.health?.extraction_mode === "hosted_replay" && run.synthetic} inspect={inspect} />)}
  </div>;
}

function RecordDecision({ w, record, suggestion, simulation, inspect }: { w: Controller; record: RecordRow; suggestion?: Suggestion; simulation: boolean; inspect: (id: string) => void }) {
  const decision = w.run!.decisions[record.record_id];
  const [outcome, setOutcome] = useState(decision?.status || (suggestion?.output ? "accepted" : "rejected"));
  const [reason, setReason] = useState(decision?.reason || "");
  const [reviewer, setReviewer] = useState(decision?.reviewer || w.run!.operator);
  const [correction, setCorrection] = useState(JSON.stringify(decision?.output || suggestion?.output || { entities: [], relations: [] }, null, 2));
  const disabled = !!w.busy || w.cooldown > 0;
  const simulationReason = `SYNTHETIC replay package: ${outcome} without human review`;
  return <Panel title={`Row ${record.locator.row} · ${record.work_order_id || record.record_id}`}>
    <div className="flex flex-wrap items-center gap-2"><Badge t={decision?.status === "rejected" ? "danger" : decision?.status === "corrected" ? "info" : decision ? "ok" : "warn"}>{decision?.status || "pending"}</Badge><Button onClick={() => inspect(record.record_id)}>Inspect source and decision</Button></div>
    <p className="whitespace-pre-wrap text-base leading-relaxed">{record.text_norm}</p>
    {suggestion?.output ? <div className="overflow-x-auto"><table className="w-full text-left text-sm"><caption className="mb-2 text-left text-fg-3">Proposed source spans · {suggestion.model_id}</caption><thead><tr><th className="p-2">Text</th><th className="p-2">Type</th><th className="p-2">Offsets</th></tr></thead><tbody>{suggestion.output.entities.map(entity => <tr key={entity.id} className="border-t border-line"><td className="p-2">{entity.text}</td><td className="p-2">{entity.type}</td><td className="p-2 font-mono text-xs">{entity.start}–{entity.end}</td></tr>)}</tbody></table></div> : <Note>No valid model annotation is available. Manual corrected annotation remains available.</Note>}
    {!!suggestion?.errors.length && <div role="note" className="text-sm text-danger">{suggestion.errors.join("; ")}</div>}
    <fieldset disabled={disabled} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2"><Field label="Record decision"><select className={inputClass} value={outcome} onChange={event => setOutcome(event.target.value)}>
        <option value="accepted" disabled={!suggestion?.output}>Accept proposal</option><option value="corrected" disabled={simulation}>Correct annotation</option><option value="rejected">Reject record</option>
      </select></Field><Field label="Record reviewer"><input className={inputClass} value={simulation ? "SYNTHETIC DEMO SIMULATOR" : reviewer} disabled={simulation} onChange={event => setReviewer(event.target.value)} /></Field></div>
      {outcome === "corrected" && <Field label="Corrected annotation (entities and relations JSON)"><textarea spellCheck={false} rows={12} className={inputClass + " font-mono text-xs"} value={correction} onChange={event => setCorrection(event.target.value)} /><Note>Offsets refer to the normalized source text above. The backend validates labels, spans and relations before saving.</Note></Field>}
      <Field label="Record decision reason"><textarea className={inputClass} value={simulation ? simulationReason : reason} disabled={simulation} onChange={event => setReason(event.target.value)} /></Field>
      <Button primary disabled={!simulation && (!reason.trim() || !reviewer.trim())} onClick={() => void w.perform("Saving record decision", async () => {
        let output;
        if (outcome === "corrected") {
          try { output = JSON.parse(correction); } catch { throw new Error("Correction must be valid annotation JSON. Nothing has been saved."); }
        }
        // perform owns the mutation lock; send once rather than nesting another locked action.
        const run = w.run!;
        await w.select(await request<Run>(`/runs/${run.run_id}/records/${record.record_id}`, { expected_revision: run.revision, status: outcome,
          reason: simulation ? simulationReason : reason, reviewer: simulation ? "SYNTHETIC DEMO SIMULATOR" : reviewer, ...(output ? { correction: output } : {}) }));
      })}>Save record decision</Button>
    </fieldset>
    {decision && <details><summary className="cursor-pointer text-sm">Saved reviewer attribution</summary><JsonView value={decision} /></details>}
  </Panel>;
}
