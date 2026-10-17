import { useEffect, useState } from "react";
import { Badge, cx, Wordmark } from "../../components/ui/primitives";
import { SourceStage, MappingStage } from "./SourceMapping";
import { ReviewStage } from "./ReviewStage";
import { FactsStage, EvidenceStage, ReportStage } from "./Investigation";
import { useWorkflow } from "./useWorkflow";
import { resolveReference, STAGES, stageStates } from "./workflow";
import { request, type Run } from "./api";
import { Button, JsonView, Note, Panel } from "./ui";
export type Controller = ReturnType<typeof useWorkflow>;

export function ConnectedWorkspace() {
  const w = useWorkflow();
  const [stage, setStage] = useState(0);
  const [reference, setReference] = useState<string | null>(null);
  const [allowLive, setAllowLive] = useState(false);
  const [simulation, setSimulation] = useState(() => localStorage.getItem("ignis-simulated-replay") === "true");
  const statuses = stageStates(w.run);
  const selected = w.run && reference ? resolveReference(w.run, reference) : null;
  const disabled = !!w.busy || w.cooldown > 0;
  const setSimulated = (value: boolean) => { setSimulation(value); localStorage.setItem("ignis-simulated-replay", String(value)); };
  const inspect = (id: string) => setReference(id);
  useEffect(() => { setReference(null); }, [w.run?.run_id, w.run?.revision]);
  useEffect(() => {
    if (!reference) return;
    const previous = document.activeElement as HTMLElement | null;
    const close = document.getElementById("close-evidence-inspector");
    close?.focus();
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setReference(null); };
    window.addEventListener("keydown", onKey);
    return () => { window.removeEventListener("keydown", onKey); previous?.focus(); };
  }, [reference]);
  return <div className="flex min-h-dvh flex-col bg-bg text-fg">
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-elevated px-4 py-3">
      <a href="#/" aria-label="Back to landing page"><Wordmark height={18} /></a>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <Badge t="info">Workflow API workspace</Badge>
        {w.health && <><Badge t={w.health.extraction_mode === "hosted_live" ? "warn" : "plain"}>Server: {w.health.extraction_mode}</Badge><Badge t="synthetic">Evidence: {w.health.corpus_mode}</Badge></>}
        {w.run && <Badge t={w.run.synthetic ? "synthetic" : "plain"}>{w.run.synthetic ? "Synthetic input" : "User supplied input"}</Badge>}
        {w.run?.suggestions.length ? <Badge>Saved extraction: {[...new Set(w.run.suggestions.map(s => s.adapter_mode))].join(", ")}</Badge> : null}
        {(w.health?.extraction_mode === "hosted_live" || w.health?.explanation_mode === "hosted_live") && <label className="flex items-center gap-2 text-warn"><input type="checkbox" checked={allowLive} onChange={event => setAllowLive(event.target.checked)} />Enable live calls (shared quota)</label>}
        <Button disabled={disabled} onClick={() => void w.refresh()}>Refresh saved state</Button>
      </div>
    </header>
    <div className="flex flex-1 flex-col lg:flex-row">
      <aside className="border-b border-line bg-elevated p-4 lg:w-64 lg:shrink-0 lg:border-r lg:border-b-0">
        <label className="block text-sm">Saved runs
          <select aria-label="Saved runs" className="mt-2 w-full rounded-lg border border-line-strong bg-bg p-2 text-sm" value={w.run?.run_id || ""} disabled={disabled}
            onChange={event => { const id = event.target.value; if (id) void w.perform("Loading run", async () => w.select(await request<Run>(`/runs/${id}`))); }}>
            <option value="">Choose a saved run</option>{w.runs.map(run => <option key={run.run_id} value={run.run_id}>{run.name} · {run.run_id}</option>)}
          </select>
        </label>
        {w.run && <div className="my-4 space-y-1 break-all font-mono text-xs text-fg-3"><p>{w.run.run_id}</p><p>Saved revision {w.run.revision}</p><p>{w.run.filename || "No source uploaded"}</p></div>}
        <nav aria-label="Workflow stages" className="mt-4 overflow-x-auto"><ol className="flex min-w-max gap-1 lg:flex-col">
          {STAGES.map((name, index) => <li key={name}><button type="button" aria-current={stage === index ? "step" : undefined} onClick={() => { setStage(index); setReference(null); }}
            className={cx("flex w-full items-center justify-between gap-4 rounded-lg px-3 py-2 text-left text-sm", stage === index ? "bg-hover text-brand-text" : "text-fg-2 hover:bg-hover")}>
            <span>{index + 1}. {name}</span><span className="text-xs text-fg-3">{statuses[index]}</span>
          </button></li>)}
        </ol></nav>
        {w.health && <details className="mt-5 text-xs text-fg-3"><summary className="cursor-pointer">Provider details</summary><JsonView value={w.health} /></details>}
      </aside>
      <main className="min-w-0 flex-1 p-4 sm:p-6" aria-busy={!!w.busy}>
        <div className="mx-auto max-w-5xl space-y-5">
          <div><h1 className="text-3xl font-semibold">{STAGES[stage]}</h1><Note>Changes are saved by the workflow API. Numeric facts and report permissions come from the backend.</Note></div>
          <div aria-live="polite" role="status">{w.busy && <p className="rounded-lg border border-info/30 p-3 text-sm text-info">{w.busy}… Existing facts and evidence remain readable.</p>}</div>
          {w.error && <div role="alert" className="rounded-xl border border-danger/40 bg-danger/10 p-4 text-sm text-danger">{w.error}{w.cooldown > 0 && <p>Retry available in {w.cooldown}s. No automatic retries are sent.</p>}</div>}
          {!!w.run?.stage_errors?.length && <Panel title="Stage errors"><JsonView value={w.run.stage_errors} /></Panel>}
          {stage === 0 && <SourceStage w={w} next={() => setStage(1)} setSimulation={setSimulated} />}
          {stage > 0 && !w.run && <Note>Create or choose a saved run in Source first.</Note>}
          {stage === 1 && w.run && <MappingStage key={w.run.run_id + ":" + w.run.source_sha256} w={w} next={() => setStage(2)} simulation={simulation} />}
          {stage === 2 && w.run && <ReviewStage key={w.run.run_id} w={w} next={() => setStage(3)} simulation={simulation} setSimulation={setSimulated} inspect={inspect} allowLive={allowLive} />}
          {stage === 3 && w.run && <FactsStage key={w.run.run_id} w={w} next={() => setStage(4)} simulation={simulation} inspect={inspect} />}
          {stage === 4 && w.run && <EvidenceStage key={w.run.run_id} w={w} next={() => setStage(5)} inspect={inspect} allowLive={allowLive} />}
          {stage === 5 && w.run && <ReportStage w={w} inspect={inspect} />}
          {w.run && <details className="rounded-xl border border-line p-4 text-sm"><summary className="cursor-pointer">Saved audit history ({w.history.length} events)</summary>
            <ol className="mt-3 space-y-2">{w.history.map(event => <li key={event.revision}><details><summary className="cursor-pointer font-mono text-xs">Revision {event.revision}: {event.kind}</summary><JsonView value={event.data} /></details></li>)}</ol>
          </details>}
        </div>
      </main>
    </div>
    {reference && <div className="fixed inset-0 z-50 flex justify-end bg-black/70" onClick={() => setReference(null)}>
      <aside role="dialog" aria-modal="true" aria-label="Evidence inspector" className="h-full w-full max-w-xl overflow-auto border-l border-line bg-elevated p-5" onClick={event => event.stopPropagation()}
        onKeyDown={event => { if (event.key !== "Tab") return; const controls = event.currentTarget.querySelectorAll<HTMLElement>("button, a[href], summary, [tabindex='0']"); const first = controls[0], last = controls[controls.length - 1]; if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); } else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); } }}>
        <Button id="close-evidence-inspector" onClick={() => setReference(null)}>Close inspector</Button>
        <h2 className="my-4 break-all text-xl">{selected?.title || reference}</h2>
        {selected ? <><JsonView value={selected.value} /><div className="mt-4 flex flex-wrap gap-2">{selected.records.map(id => <Button key={id} onClick={() => inspect(id)}>Open source {id}</Button>)}</div></> : <Note>This reference is unavailable in the current saved snapshot. Reload or inspect the relevant historical PDF.</Note>}
      </aside>
    </div>}
  </div>;
}
