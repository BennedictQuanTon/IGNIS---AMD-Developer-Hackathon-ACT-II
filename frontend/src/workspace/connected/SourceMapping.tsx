import { useState } from "react";
import type { Controller } from "./ConnectedWorkspace";
import { filePayload, request, type DemoInput, type Run } from "./api";
import { Button, Field, inputClass, JsonView, Note, Panel } from "./ui";

export function SourceStage({ w, next, setSimulation }: { w: Controller; next: () => void; setSimulation: (value: boolean) => void }) {
  const [name, setName] = useState("Maintenance review");
  const [operator, setOperator] = useState("local-reviewer");
  const [synthetic, setSynthetic] = useState(true);
  const disabled = !!w.busy || w.cooldown > 0;
  return <div className="space-y-4">
    <Panel title="Create a run">
      <fieldset disabled={disabled} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2"><Field label="Run name"><input className={inputClass} value={name} onChange={event => setName(event.target.value)} /></Field>
          <Field label="Operator"><input className={inputClass} value={operator} onChange={event => setOperator(event.target.value)} /></Field></div>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={synthetic} onChange={event => setSynthetic(event.target.checked)} />Input is synthetic demonstration data</label>
        <Button primary disabled={!name.trim() || !operator.trim() || !w.health} onClick={() => void w.perform("Creating run", async () => {
          await w.create({ name, operator, synthetic, adapter_mode: w.health?.extraction_mode === "unavailable" ? "unavailable" : "injected" }); setSimulation(false);
        })}>Create run</Button>
        {w.health?.demo_input_available && <><Button onClick={() => void w.perform("Loading recorded demo input", async () => {
          const input = await request<DemoInput>("/demo-input");
          const run = await w.create({ name: input.name, operator: input.operator, synthetic: true, adapter_mode: "injected" });
          await w.select(await request<Run>(`/runs/${run.run_id}/upload`, { filename: input.filename, csv_text: input.csv_text, expected_revision: run.revision }));
          setSimulation(true); next();
        })}>Load recorded demo input</Button><Note>The recorded walkthrough uses synthetic input and explicitly simulated record decisions. Its explanation matches the original input, decisions, criticality and query; edits can produce a replay miss.</Note></>}
      </fieldset>
    </Panel>
    {w.run && <Panel title="Source upload and original rows">
      <Note>Uploading another file invalidates the mapping, analysis, evidence and signoff. Historical issued PDFs remain in report history.</Note>
      <Field label="Upload maintenance export (CSV, TSV, JSON, JSONL or XLSX)"><input className={inputClass} type="file" accept=".csv,.tsv,.json,.jsonl,.xlsx" disabled={disabled} onChange={event => {
        const file = event.target.files?.[0]; if (file) void w.perform("Uploading source", async () => {
          const payload = await filePayload(file); const run = w.run!;
          await w.select(await request<Run>(`/runs/${run.run_id}/upload`, { ...payload, expected_revision: run.revision })); setSimulation(false);
        }); event.target.value = "";
      }} /></Field>
      <dl className="grid gap-3 break-all text-sm sm:grid-cols-2"><div><dt>File</dt><dd>{w.run.filename || "None"}</dd></div><div><dt>Source SHA-256</dt><dd className="font-mono text-xs">{w.run.source_sha256 || "Not uploaded"}</dd></div><div><dt>Rows</dt><dd>{w.run.row_count ?? 0}</dd></div></dl>
      <details><summary className="cursor-pointer">Unmodified source preview</summary><JsonView value={w.run.raw_rows || []} /></details>
      <Button primary disabled={!w.run.proposal || disabled} onClick={next}>Continue to mapping</Button>
    </Panel>}
  </div>;
}

export function MappingStage({ w, next, simulation }: { w: Controller; next: () => void; simulation: boolean }) {
  const run = w.run!;
  const [mapping, setMapping] = useState<Record<string, string | null>>(run.proposal?.mapping || {});
  const [reason, setReason] = useState(simulation ? "synthetic headers" : "");
  const disabled = !!w.busy || w.cooldown > 0;
  if (!run.proposal) return <Note>Upload a source file before confirming a mapping.</Note>;
  return <div className="space-y-4"><Panel title="Confirm column mapping">
    <Note>Proposals remain unconfirmed until you save a reason. Reconfirmation clears all downstream decisions.</Note>
    <fieldset disabled={disabled} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">{Object.keys(mapping).map(field => <Field key={field} label={field}><select className={inputClass} value={mapping[field] || ""} onChange={event => setMapping(previous => ({ ...previous, [field]: event.target.value || null }))}>
        <option value="">Not mapped</option>{run.columns?.map(column => <option key={column}>{column}</option>)}
      </select></Field>)}</div>
      <Field label="Mapping confirmation reason"><textarea className={inputClass} value={reason} onChange={event => setReason(event.target.value)} /></Field>
      <Button primary disabled={!reason.trim()} onClick={() => void w.mutate("/mapping/confirm", { mapping, reason }, "Confirming mapping")}>Confirm mapping</Button>
      <Button disabled={!run.mapping} onClick={next}>Continue to review</Button>
    </fieldset>
    {run.mapping && <details><summary className="cursor-pointer">Saved mapping and attribution</summary><JsonView value={run.mapping} /></details>}
  </Panel><Panel title="Validation issues"><JsonView value={run.row_issues || []} /><Note>Invalid numeric fields remain visible and cannot become invented KPI values.</Note></Panel></div>;
}
