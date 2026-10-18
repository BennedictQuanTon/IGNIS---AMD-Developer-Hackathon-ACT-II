import { useEffect, useRef, useState, type ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";
import { Badge, cx, Wordmark, type Tone } from "../../components/ui/primitives";
import { Icon } from "../../components/ui/icons";
import { EASE } from "../../components/ui/motion";
import { reportUrl, request, type Claim, type DemoInput, type Draft, type Run } from "./api";
import { EvidenceInspector } from "./EvidenceInspector";
import { useWorkflow } from "./useWorkflow";
import { Button, Field, inputClass, Note } from "./ui";

type Controller = ReturnType<typeof useWorkflow>;

// The replay package (docs/benchmarks/replay) only matches these exact values: operator, mapping, record status,
// record reviewer, criticality and evidence query all feed the snapshot or evidence-pack identity.
const SCENARIO = {
  mappingReason: "synthetic headers",
  recordReviewer: "SYNTHETIC DEMO SIMULATOR",
  criticality: { component: "seal", value: 3, reason: "Synthetic demo policy value", set_by: "synthetic" },
  component: "seal",
  query: "seal leakage flush",
  signoffReviewer: "SYNTHETIC DEMO SIGNOFF SIMULATOR",
};
const DEMO_KEY = "ignis-demo-run";
const CHAR_MS = 14;
const PAUSE_MS = 900;

type StepId = "create" | "upload" | "mapping" | "extract" | "review" | "analyze" | "context" | "generate" | "expert" | "issue" | "done";
const RAIL = ["Source", "Mapping", "Record review", "Facts", "Evidence", "Expert signoff", "Report"] as const;
const STAGE_OF: Record<StepId, number> = { create: 0, upload: 0, mapping: 1, extract: 2, review: 2, analyze: 3, context: 4, generate: 4, expert: 5, issue: 6, done: 6 };
const LABEL: Record<StepId, string> = {
  create: "Open a run for the recorded export",
  upload: "Upload the recorded maintenance export",
  mapping: "Confirm the proposed column mapping",
  extract: "Replay the recorded model extraction",
  review: "Record a decision for each extracted row",
  analyze: "Compute facts and deterministic alerts",
  context: "Retrieve applicable evidence",
  generate: "Replay the recorded cited explanation",
  expert: "Your turn: sign off the finding as the expert",
  issue: "Issue the evidence-linked PDF",
  done: "Demo run complete",
};

const OUTCOMES = [
  { id: "accepted", label: "Accept finding", effect: "Signs the drafted finding as written. IGNIS then issues the PDF.",
    reason: "Hypotheses are consistent with the cited facts and the inspection guidance." },
  { id: "corrected", label: "Correct finding", effect: "Withholds the weaker hypothesis and adds your note. The PDF carries your corrected version.",
    reason: "A single failed-state record is too thin to keep as a hypothesis." },
  { id: "rejected", label: "Reject finding", effect: "Blocks the report. Facts and evidence stay available for another review.",
    reason: "The cited evidence does not support these hypotheses for this asset." },
  { id: "inconclusive", label: "Inconclusive", effect: "Keeps the finding open. The report stays blocked until you decide.",
    reason: "A site inspection is needed before signoff." },
] as const;
type Outcome = (typeof OUTCOMES)[number]["id"];
const DEFAULT_NOTE = "Expert correction: the withheld hypothesis rests on a single record and needs inspection before it is reported.";

function nextStep(run: Run | null): StepId {
  if (!run) return "create";
  if (!run.source_sha256) return "upload";
  if (!run.mapping) return "mapping";
  if (!run.suggestions.length) return "extract";
  if (run.records.some(record => !run.decisions[record.record_id])) return "review";
  if (!run.snapshot) return "analyze";
  if (!run.context) return "context";
  if (!run.draft_result) return "generate";
  const review = run.expert_reviews.at(-1);
  if (!review || !["accepted", "corrected"].includes(review.decision)) return "expert";
  return run.latest_report ? "done" : "issue";
}
function blockedReason(run: Run | null): string | null {
  if (!run) return null;
  const s = run.stage_status;
  if (s.upload === "failed") return "The recorded export could not be parsed.";
  if (s.extraction === "failed" || s.extraction === "unavailable") return "The recorded extraction could not be replayed: " + (run.stage_errors || []).join("; ");
  if (run.context && run.context.status !== "ready") return `Evidence retrieval returned ${run.context.status}. ${run.context.reason || ""}`;
  if (run.draft_result && run.draft_result.status !== "pending_expert_review") return `The explanation replay returned ${run.draft_result.status}: ${run.draft_result.errors.join("; ")}`;
  return null;
}
const pendingRecord = (run: Run) => run.records.find(record => !run.decisions[record.record_id]);
const recordStatus = (run: Run, id: string) => run.suggestions.find(s => s.record_id === id)?.output ? "accepted" : "rejected";
const recordReason = (status: string) => `SYNTHETIC replay package: ${status} without human review`;
const assetOf = (run: Run) => run.records.find(record => record.asset_id)?.asset_id || "";
function correctedDraft(draft: Draft, note: string): Draft {
  return { ...draft, hypotheses: draft.hypotheses.length > 1 ? draft.hypotheses.slice(0, -1) : draft.hypotheses, uncertainty: `${draft.uncertainty} ${note.trim()}`.trim() };
}

/** Text that the autopilot types into the console for a step; its length paces the step. */
function typedFor(step: StepId, run: Run | null, input: DemoInput | null): string[] {
  if (step === "create") return input ? [input.name, input.operator] : [];
  if (step === "upload") return input ? [input.filename] : [];
  if (step === "mapping") return [SCENARIO.mappingReason, ...Object.values(run?.proposal?.mapping || {}).map(value => value || "")];
  if (step === "review" && run) { const record = pendingRecord(run); return record ? [recordReason(recordStatus(run, record.record_id))] : []; }
  if (step === "analyze") return [SCENARIO.criticality.component, String(SCENARIO.criticality.value), SCENARIO.criticality.reason];
  if (step === "context") return [run ? assetOf(run) : "", SCENARIO.component, SCENARIO.query];
  return [];
}

type Mode = "continuous" | "manual";
const MODE_KEY = "ignis-demo-mode";
const ACTION: Partial<Record<StepId, string>> = {
  create: "Open run", upload: "Upload recorded export", mapping: "Confirm mapping", extract: "Start extraction", review: "Save record decision",
  analyze: "Analyze approved records", context: "Retrieve evidence", generate: "Generate explanation", issue: "Issue approved PDF",
};
/** `free` fields accept any text; the others must equal the recorded value for the replay to match. */
type ManualField = { key: string; label: string; expected: string; free?: boolean; options?: { value: string; label: string }[]; wide?: boolean };
function manualFields(step: StepId, run: Run | null, input: DemoInput | null): ManualField[] {
  if (step === "create") return input ? [{ key: "name", label: "Run name", expected: input.name, free: true }, { key: "operator", label: "Operator", expected: input.operator }] : [];
  if (step === "mapping") {
    const options = ["", ...(run?.columns || [])].map(column => ({ value: column, label: column || "Not mapped" }));
    return [...Object.entries(run?.proposal?.mapping || {}).map(([field, column]) => ({ key: `map:${field}`, label: field, expected: column || "", options })),
      { key: "reason", label: "Confirmation reason", expected: SCENARIO.mappingReason, wide: true }];
  }
  if (step === "review" && run) {
    const record = pendingRecord(run);
    if (!record) return [];
    const status = recordStatus(run, record.record_id);
    return [{ key: "status", label: "Record decision", expected: status, options: [{ value: "", label: "Choose a decision" }, { value: "accepted", label: "Accept proposal" }, { value: "rejected", label: "Reject record" }] },
      { key: "reason", label: "Record decision reason", expected: recordReason(status), free: true, wide: true }];
  }
  if (step === "analyze") return [{ key: "component", label: "Critical component", expected: SCENARIO.criticality.component },
    { key: "value", label: "Criticality multiplier", expected: String(SCENARIO.criticality.value) }, { key: "reason", label: "Criticality reason", expected: SCENARIO.criticality.reason }];
  if (step === "context") return [{ key: "asset", label: "Evidence asset", expected: run ? assetOf(run) : "" },
    { key: "component", label: "Evidence component", expected: SCENARIO.component }, { key: "query", label: "Evidence query", expected: SCENARIO.query, wide: true }];
  return [];
}
const sameText = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase();

function ManualStep({ step, fields, busy, note, onSubmit }: { step: StepId; fields: ManualField[]; busy: boolean; note?: string; onSubmit: (values: Record<string, string>) => void }) {
  const [values, setValues] = useState<Record<string, string>>(() => Object.fromEntries(fields.map(f => [f.key, f.key.startsWith("map:") ? f.expected : ""])));
  const valid = (f: ManualField) => (f.free ? !!values[f.key]?.trim() : f.options ? values[f.key] === f.expected : sameText(values[f.key] || "", f.expected));
  return <div className="space-y-3 rounded-lg border border-accent/40 bg-accent-soft p-3">
    <p className="text-sm font-medium text-brand-text">Your turn: {LABEL[step].replace(/^Your turn: /, "")}</p>
    {note && <Note>{note}</Note>}
    {!!fields.length && <div className="grid gap-3 sm:grid-cols-2">{fields.map(f => {
      const value = values[f.key] || "";
      const set = (next: string) => setValues(previous => ({ ...previous, [f.key]: next }));
      const wrong = !f.free && value !== "" && !valid(f);
      const shown = f.options?.find(option => option.value === f.expected)?.label || f.expected;
      return <div key={f.key} className={cx("min-w-0", f.wide && "sm:col-span-2")}>
        <Field label={f.label}>{f.options
          ? <select className={inputClass} value={value} onChange={event => set(event.target.value)}>{f.options.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select>
          : <input className={inputClass} value={value} placeholder={f.expected} onChange={event => set(event.target.value)} />}</Field>
        {wrong && <p className="mt-1 text-xs text-warn">The recording was made with “{shown}”. Another value would miss the replay.</p>}
      </div>;
    })}</div>}
    <div className="flex flex-wrap gap-2">
      <Button primary disabled={busy || !fields.every(valid)} onClick={() => onSubmit(values)}>{ACTION[step]}</Button>
      {!!fields.length && <Button disabled={busy} onClick={() => setValues(previous => ({ ...previous, ...Object.fromEntries(fields.map(f => [f.key, f.free && previous[f.key]?.trim() ? previous[f.key] : f.expected])) }))}>Fill recorded values</Button>}
    </div>
  </div>;
}

function useTyped(text: string, active: boolean, speed: number) {
  const reduce = useReducedMotion();
  const [count, setCount] = useState(active && !reduce ? 0 : text.length);
  useEffect(() => {
    if (!active || reduce) { setCount(text.length); return; }
    setCount(0);
    const started = performance.now();
    let frame = 0;
    const tick = () => {
      const typed = Math.min(text.length, Math.floor(((performance.now() - started) * speed) / CHAR_MS));
      setCount(typed);
      if (typed < text.length) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [text, active, reduce, speed]);
  return text.slice(0, count);
}

/** Looks and focuses like an input; the value is pinned to the recorded scenario. */
function ConsoleField({ label, value, typing, speed, wide }: { label: string; value: string; typing: boolean; speed: number; wide?: boolean }) {
  const shown = useTyped(value, typing, speed);
  const [hint, setHint] = useState(false);
  return <div className={cx("min-w-0", wide && "sm:col-span-2")}><Field label={label}>
    <span className="relative block">
      <input readOnly value={shown} onFocus={() => setHint(true)} onBlur={() => setHint(false)} onKeyDown={() => setHint(true)}
        className={cx(inputClass, "pr-8 font-mono text-[13px] transition-[border-color,box-shadow] duration-200", typing && "border-accent/70 shadow-[0_0_0_3px_rgb(255_196_0/0.12)]")} />
      <Icon name="lock" size={13} className="pointer-events-none absolute top-1/2 right-2.5 -translate-y-1/2 text-fg-4" />
    </span>
  </Field>{hint && <p className="mt-1 text-xs text-fg-4">Pinned to the recorded scenario; the replay only matches this value.</p>}</div>;
}

function Ref({ id, inspect }: { id: string; inspect: (id: string) => void }) {
  return <button type="button" className="rounded border border-line-strong px-2 py-0.5 font-mono text-[11px] text-info hover:bg-hover" onClick={() => inspect(id)}>{id}</button>;
}

type CardState = "done" | "current" | "waiting" | "upcoming";
const CARD_BADGE: Record<CardState, [Tone, string]> = { done: ["ok", "Done"], current: ["info", "In progress"], waiting: ["accent", "Your decision"], upcoming: ["neutral", "After signoff"] };

function StageCard({ index, title, state, children }: { index: number; title: string; state: CardState; children: ReactNode }) {
  return <motion.section id={`demo-stage-${index}`} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: EASE }}
    className={cx("scroll-mt-36 rounded-xl border bg-elevated", state === "current" ? "border-accent/50" : state === "waiting" ? "border-accent" : "border-line")}>
    <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
      <h2 className="font-semibold"><span className="mr-2 font-mono text-xs text-fg-4">{String(index + 1).padStart(2, "0")}</span>{title}</h2>
      <Badge t={CARD_BADGE[state][0]}>{CARD_BADGE[state][1]}</Badge>
    </header>
    <div className="space-y-4 p-4">{children}</div>
  </motion.section>;
}

function ClaimView({ claim, inspect, struck }: { claim: Claim; inspect: (id: string) => void; struck?: boolean }) {
  return <div className={cx("space-y-2 rounded-lg border border-line p-3", struck && "opacity-50")}>
    <p className={cx(struck && "line-through")}>{claim.text}</p>
    <div className="flex flex-wrap gap-1.5">{claim.citations.map(id => <Ref key={id} id={id} inspect={inspect} />)}</div>
  </div>;
}

export function DemoRun() {
  const w = useWorkflow();
  const reduce = useReducedMotion();
  const [demoId, setDemoId] = useState<string | null>(() => localStorage.getItem(DEMO_KEY));
  const [input, setInput] = useState<DemoInput | null>(null);
  const [playing, setPlaying] = useState(false);
  const [mode, setModeState] = useState<Mode>(() => (localStorage.getItem(MODE_KEY) === "manual" ? "manual" : "continuous"));
  const [speed, setSpeed] = useState(1);
  const [reference, setReference] = useState<string | null>(null);
  const run = w.run && w.run.run_id === demoId ? w.run : null;
  const step = nextStep(run);
  const stage = STAGE_OF[step];
  const blocked = blockedReason(run);
  const replay = w.health?.extraction_mode === "hosted_replay" && w.health?.explanation_mode === "hosted_replay";
  const ready = replay && !!input;
  const remember = (id: string | null) => { setDemoId(id); if (id) localStorage.setItem(DEMO_KEY, id); else localStorage.removeItem(DEMO_KEY); };

  const { setError } = w;
  const inputAvailable = !!w.health?.demo_input_available;
  useEffect(() => {
    if (!inputAvailable || input) return;
    request<DemoInput>("/demo-input").then(setInput, () => setError("The recorded demo input could not be loaded. Reconnect to retry."));
  }, [inputAvailable, input, setError]);
  // Resume the saved demo run after a reload; a restarted free-tier server forgets it.
  const resume = useRef(true);
  useEffect(() => {
    if (!resume.current || !w.health || w.busy) return;
    resume.current = false;
    if (!demoId || w.run?.run_id === demoId) return;
    if (!w.runs.some(value => value.run_id === demoId)) { remember(null); return; }
    void w.perform("Restoring the demo run", async () => w.select(await request<Run>(`/runs/${demoId}`)));
  });

  const act = (target: StepId, values: Record<string, string> = {}) => {
    const current = w.run;
    switch (target) {
      case "create": return w.perform("Opening a demo run", async () => {
        const created = await w.create({ name: values.name?.trim() || input!.name, operator: input!.operator, synthetic: true, adapter_mode: "injected" });
        remember(created.run_id);
      });
      case "upload": return w.perform("Uploading the recorded export", async () => {
        await w.select(await request<Run>(`/runs/${current!.run_id}/upload`, { filename: input!.filename, csv_text: input!.csv_text, expected_revision: current!.revision }));
      });
      case "mapping": return w.mutate("/mapping/confirm", { mapping: current!.proposal!.mapping, reason: SCENARIO.mappingReason }, "Confirming the column mapping");
      case "extract": return w.mutate("/extraction/start", {}, "Replaying the recorded extraction");
      case "review": {
        const record = pendingRecord(current!)!;
        const status = recordStatus(current!, record.record_id);
        return w.mutate(`/records/${record.record_id}`, { status, reason: values.reason?.trim() || recordReason(status), reviewer: SCENARIO.recordReviewer }, `Saving the decision for row ${record.locator.row}`);
      }
      case "analyze": return w.mutate("/analyze", { criticalities: [SCENARIO.criticality] }, "Computing facts and alerts");
      case "context": return w.mutate("/context", { asset_id: assetOf(current!), component: SCENARIO.component, query: SCENARIO.query }, "Retrieving applicable evidence");
      case "generate": return w.mutate("/context/generate", {}, "Replaying the recorded explanation");
      case "issue": return w.mutate("/reports/issue", {}, "Rendering the PDF");
    }
  };
  const actRef = useRef(act);
  actRef.current = act;

  const automatic = step !== "expert" && step !== "done";
  const canAct = ready && !w.busy && !w.error && !blocked && automatic && w.cooldown === 0;
  const typing = typedFor(step, run, input);
  const delay = (Math.max(0, ...typing.map(text => text.length)) * CHAR_MS + PAUSE_MS) / speed;
  useEffect(() => {
    if (!playing || !canAct) return;
    const timer = window.setTimeout(() => void actRef.current(step), delay);
    return () => window.clearTimeout(timer);
  }, [playing, canAct, step, run?.revision, delay]);
  useEffect(() => { if (w.error || blocked) setPlaying(false); }, [w.error, blocked]);
  const finished = step === "done";
  const manual = mode === "manual";
  useEffect(() => {
    if (!playing && !manual) return;
    document.getElementById(`demo-stage-${stage}`)?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  }, [stage, finished, playing, manual, reduce]);
  useEffect(() => { setReference(null); }, [run?.run_id]);

  const setMode = (next: Mode) => {
    setModeState(next);
    localStorage.setItem(MODE_KEY, next);
    w.setError("");
    setPlaying(next === "continuous" && !!run && automatic);
  };
  const start = (next: Mode = mode) => { remember(null); setModeState(next); localStorage.setItem(MODE_KEY, next); w.setError(""); setPlaying(next === "continuous"); };
  const typingNow = (target: StepId) => playing && step === target && canAct;
  const status = w.busy ? `${w.busy}…` : blocked ? "Stopped: the run left the recorded scenario." : w.error ? "Stopped on an error." : !run && !playing && !manual ? "Ready when you are."
    : manual ? (automatic ? `Your step: ${LABEL[step]}` : LABEL[step]) : playing && automatic ? `Next: ${LABEL[step]}` : LABEL[step];
  const manualStep = (target: StepId, note?: string) => manual && step === target && ready && !blocked
    ? <ManualStep key={`${target}:${run ? pendingRecord(run)?.record_id || "" : ""}`} step={target} fields={manualFields(target, run, input)} busy={!!w.busy} note={note} onSubmit={values => void act(target, values)} />
    : null;

  return <div className="flex min-h-dvh flex-col bg-bg text-fg">
    <header className="sticky top-0 z-40 border-b border-line bg-elevated/95 backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div className="flex items-center gap-3"><a href="#/" aria-label="Back to landing page"><Wordmark height={18} /></a><span className="text-sm text-fg-3">Demo run</span></div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {w.health && <span className="inline-flex items-center gap-1.5 text-fg-3" title={`Extraction ${w.health.extraction_model} · explanation ${w.health.explanation_model} · ${w.health.explanation_prompt}`}><Icon name="replay" size={14} />{replay ? "Recorded replay" : "Not a replay server"}</span>}
          <Badge t="synthetic">Synthetic data</Badge>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 border-t border-line px-4 py-2">
        <div role="group" aria-label="Demo mode" className="flex rounded-lg border border-line-strong p-0.5">
          {(["continuous", "manual"] as const).map(value => <button key={value} type="button" aria-pressed={mode === value} disabled={!!w.busy} onClick={() => setMode(value)}
            className={cx("rounded-md px-3 py-1.5 text-sm transition-colors", mode === value ? "bg-hover text-fg" : "text-fg-3 hover:text-fg")}>{value === "continuous" ? "Continuous" : "Manual"}</button>)}
        </div>
        {manual
          ? run && <Button disabled={!!w.busy} onClick={() => start()}><Icon name="replay" size={14} />Start over</Button>
          : !run && !playing
          ? <Button primary disabled={!ready || !!w.busy} onClick={() => start()}><Icon name="play" size={14} />Start demo run</Button>
          : <>
            <Button primary={!playing && automatic} disabled={!automatic || !ready || !!blocked} onClick={() => { w.setError(""); setPlaying(value => !value); }} aria-pressed={playing}>
              <Icon name={playing ? "pause" : "play"} size={14} />{playing ? "Pause" : "Play"}</Button>
            <Button disabled={!canAct} onClick={() => void act(step)}><Icon name="step" size={14} />Step</Button>
            <Button onClick={() => setSpeed(value => (value === 1 ? 2 : 1))} aria-label={`Playback speed ${speed}×`}>{speed}×</Button>
            <Button disabled={!!w.busy} onClick={() => start()}><Icon name="replay" size={14} />Start over</Button>
          </>}
        <p role="status" aria-live="polite" className="ml-1 flex min-w-0 items-center gap-2 text-sm text-fg-2">
          {(w.busy || (playing && canAct)) && <span aria-hidden className="size-2 shrink-0 animate-pulse rounded-full bg-accent" />}
          {step === "expert" && run && !w.busy && <span aria-hidden className="size-2 shrink-0 rounded-full bg-accent" />}
          <span className="truncate">{status}</span>
        </p>
      </div>
    </header>

    <div className="flex flex-1 flex-col lg:flex-row">
      <aside className="border-b border-line bg-elevated p-4 lg:sticky lg:top-[105px] lg:h-[calc(100dvh-105px)] lg:w-60 lg:shrink-0 lg:border-r lg:border-b-0">
        <nav aria-label="Demo stages" className="overflow-x-auto"><ol className="flex min-w-max gap-1 lg:flex-col">
          {RAIL.map((name, index) => {
            const done = run && (index < stage || step === "done");
            const current = run && index === stage && step !== "done";
            return <li key={name}><button type="button" disabled={!run || index > stage} onClick={() => document.getElementById(`demo-stage-${index}`)?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" })}
              aria-current={current ? "step" : undefined}
              className={cx("flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm disabled:cursor-default", current ? "bg-hover text-fg" : done ? "text-fg-2 hover:bg-hover" : "text-fg-4")}>
              <span className={cx("grid size-5 shrink-0 place-items-center rounded-full border font-mono text-[10px]", done ? "border-ok/50 bg-ok/15 text-ok" : current ? "border-accent text-brand-text" : "border-dashed border-line-strong")}>
                {done ? <Icon name="check" size={10} /> : index + 1}</span>{name}
            </button></li>;
          })}
        </ol></nav>
        {run && <div className="mt-4 hidden space-y-1 break-all font-mono text-[11px] text-fg-4 lg:block"><p>{run.run_id}</p><p>Saved revision {run.revision}</p></div>}
      </aside>

      <main className="min-w-0 flex-1 p-4 sm:p-6" aria-busy={!!w.busy}>
        <div className="mx-auto max-w-4xl space-y-5">
          {w.error && step !== "expert" && <div role="alert" className="space-y-3 rounded-xl border border-danger/40 bg-danger/10 p-4 text-sm text-danger">
            <p>{w.error}</p>{w.cooldown > 0 && <p>Retry available in {w.cooldown}s.</p>}
            <div className="flex flex-wrap gap-2">{automatic && !manual && <Button disabled={w.cooldown > 0 || !!w.busy || !ready} onClick={() => { w.setError(""); setPlaying(true); }}>Retry step</Button>}<Button onClick={() => void w.refresh()}>Reconnect</Button></div>
          </div>}
          {blocked && <div role="alert" className="space-y-3 rounded-xl border border-warn/40 bg-warn/10 p-4 text-sm text-warn"><p>{blocked}</p><Button onClick={() => start()}>Start over</Button></div>}

          {!run && <Intro w={w} replay={replay} ready={ready} mode={mode} start={start} />}
          {!run && manual && ready && <StageCard index={0} title="Source: open a run" state="current">{manualStep("create")}</StageCard>}
          {run && <StageCards run={run} w={w} step={step} input={input} speed={speed} typingNow={typingNow} inspect={setReference} manualStep={manualStep}
            onSigned={() => { if (!manual) setPlaying(true); }} />}
        </div>
      </main>
    </div>
    <EvidenceInspector run={run} reference={reference} onClose={() => setReference(null)} inspect={setReference} />
  </div>;
}

function Intro({ w, replay, ready, mode, start }: { w: Controller; replay: boolean; ready: boolean; mode: Mode; start: (mode: Mode) => void }) {
  return <section className="rounded-xl border border-line bg-elevated p-6 sm:p-8">
    <p className="t-label">Guided demo</p>
    <h1 className="mt-3 text-3xl font-semibold">Watch one maintenance export become a signed, cited report</h1>
    <p className="mt-3 max-w-2xl leading-relaxed text-fg-2">IGNIS runs a recorded synthetic pump export through every stage: mapping, extraction review, deterministic facts, evidence retrieval and a cited explanation. When the finding is ready, you sign it off as the expert, and your decision controls whether a report is issued.</p>
    <ul className="mt-5 grid gap-3 text-sm text-fg-3 sm:grid-cols-3">
      <li className="rounded-lg border border-line p-3"><span className="text-fg">No files needed.</span> The six-row export and its model outputs are recorded, so the run is repeatable and spends no model quota.</li>
      <li className="rounded-lg border border-line p-3"><span className="text-fg">Real backend.</span> Every stage is saved by the workflow API, and the PDF is rendered on the server.</li>
      <li className="rounded-lg border border-line p-3"><span className="text-fg">You stay in control.</span> Pause, step through or speed up, inspect any fact or source, and choose the expert outcome.</li>
    </ul>
    <div className="mt-6 grid gap-3 sm:grid-cols-2">
      {([["continuous", "Watch it run", "Continuous mode plays every stage like a video and stops only for your signoff."],
        ["manual", "Fill it in yourself", "Manual mode hands you each form. Type the values or fill the recorded ones, then press each action."]] as const).map(([value, title, text]) =>
        <button key={value} type="button" disabled={!ready || !!w.busy} onClick={() => start(value)}
          className={cx("rounded-lg border p-4 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50", mode === value ? "border-accent bg-accent-soft" : "border-line-strong hover:bg-hover")}>
          <span className="flex items-center gap-2 font-medium text-fg"><Icon name={value === "continuous" ? "play" : "review"} size={14} />{title}</span>
          <span className="mt-1 block text-sm text-fg-3">{text}</span>
        </button>)}
    </div>
    <div className="mt-6 text-sm text-fg-3">
      {!w.health && !w.error && <p className="flex items-center gap-2"><span aria-hidden className="size-2 animate-pulse rounded-full bg-accent" />Connecting to the demo server. A sleeping free-tier server can take about a minute to wake.</p>}
      {w.health && !replay && <Note>This server is not in recorded-replay mode, so the guided demo is disabled to avoid live model calls. Use the manual workspace at #/app/manual instead.</Note>}
      {w.health && replay && !w.health.demo_input_available && <Note>This server has no recorded demo input configured.</Note>}
      {ready && mode === "manual" && <p>The first form is below. You can switch modes at any point; Continuous picks up from your current step.</p>}
    </div>
  </section>;
}

function StageCards({ run, w, step, input, speed, typingNow, inspect, manualStep, onSigned }: {
  run: Run; w: Controller; step: StepId; input: DemoInput | null; speed: number; typingNow: (step: StepId) => boolean; inspect: (id: string) => void;
  manualStep: (step: StepId, note?: string) => ReactNode; onSigned: () => void;
}) {
  const stage = STAGE_OF[step];
  const state = (index: number): CardState => (index < stage || step === "done" ? "done" : index > stage ? "upcoming" : step === "expert" ? "waiting" : "current");
  const pending = pendingRecord(run);
  const draft = run.draft_result?.draft;
  const extractForm = manualStep("extract");
  return <>
    <StageCard key="source" index={0} title="Source: recorded maintenance export" state={state(0)}>
      <div className="grid gap-3 sm:grid-cols-2">
        <ConsoleField label="Run name" value={run.name} typing={false} speed={speed} />
        <ConsoleField label="Operator" value={run.operator} typing={false} speed={speed} />
        <ConsoleField label="Source file" value={run.filename || input?.filename || ""} typing={typingNow("upload")} speed={speed} wide />
      </div>
      {manualStep("upload", `${input?.filename || "The recorded export"} is attached for you; no file picker is needed.`)}
      {run.raw_rows?.length ? <>
        <div className="overflow-x-auto rounded-lg border border-line"><table className="w-full text-left text-xs">
          <thead className="bg-bg text-fg-3"><tr>{run.columns?.map(column => <th key={column} className="p-2 font-medium whitespace-nowrap">{column}</th>)}</tr></thead>
          <tbody>{run.raw_rows.map((row, index) => <tr key={index} className="border-t border-line">{run.columns?.map(column => <td key={column} className="p-2 whitespace-nowrap">{row.values[column]}</td>)}</tr>)}</tbody>
        </table></div>
        <Note>{run.row_count} rows · source SHA-256 <span className="font-mono">{run.source_sha256?.slice(0, 16)}…</span></Note>
      </> : <Note>Waiting for the upload.</Note>}
    </StageCard>

    {stage >= 1 && <StageCard key="mapping" index={1} title="Mapping: confirm source columns" state={state(1)}>
      {manualStep("mapping", "IGNIS proposed these columns. Confirm them with the recorded reason.") || <div className="grid gap-3 sm:grid-cols-2">
        {Object.entries(run.mapping ? (run.mapping as { mapping: Record<string, string | null> }).mapping : run.proposal?.mapping || {}).map(([field, column]) =>
          <ConsoleField key={field} label={field} value={column || "Not mapped"} typing={typingNow("mapping")} speed={speed} />)}
        <ConsoleField label="Confirmation reason" value={SCENARIO.mappingReason} typing={typingNow("mapping")} speed={speed} wide />
      </div>}
      {run.mapping && <Note>Confirmed by {(run.mapping as { confirmed_by: string }).confirmed_by} · {run.records.length} canonical records · {(run.row_issues || []).length} validation issues</Note>}
    </StageCard>}

    {stage >= 2 && <StageCard key="review" index={2} title="Record review: model proposals and decisions" state={state(2)}>
      <Note>{run.suggestions.length ? `${run.extraction_identity?.model_id || "Recorded model"} proposed spans for each row. Proposals stay unapproved until a decision is saved; the replay uses simulated attribution, not a human reviewer.` : extractForm ? "The recorded model proposals are ready to replay." : "Replaying the recorded extraction…"}</Note>
      {extractForm}
      {!!run.suggestions.length && <ul className="space-y-2">{run.records.map(record => {
        const suggestion = run.suggestions.find(value => value.record_id === record.record_id);
        const decision = run.decisions[record.record_id];
        const current = pending?.record_id === record.record_id;
        const status = recordStatus(run, record.record_id);
        return <li key={record.record_id} className={cx("space-y-2 rounded-lg border p-3 transition-colors", current && step === "review" ? "border-accent/50 bg-accent-soft" : "border-line")}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <button type="button" className="font-mono text-xs text-fg-3 hover:text-fg" onClick={() => inspect(record.record_id)}>Row {record.locator.row} · {record.work_order_id}</button>
            <Badge t={decision ? (decision.status === "rejected" ? "danger" : "ok") : "warn"}>{decision?.status || "pending"}</Badge>
          </div>
          <p>{record.text_norm}</p>
          {suggestion?.output ? <div className="flex flex-wrap gap-1.5">{suggestion.output.entities.map(entity => <span key={entity.id} className="rounded border border-line-strong px-1.5 py-0.5 text-xs"><span className="text-fg-4">{entity.type}</span> {entity.text}</span>)}</div>
            : <p className="text-xs text-danger">{suggestion?.errors.join("; ") || "No valid proposal"}. It cannot be accepted, so it is rejected.</p>}
          {(current && manualStep("review", "Your reason is saved; the decision is attributed to SYNTHETIC DEMO SIMULATOR so the recorded explanation still matches."))
            || ((decision || (current && step === "review")) && <ConsoleField label="Decision reason" value={decision?.reason || recordReason(status)} typing={current && typingNow("review")} speed={speed} />)}
        </li>;
      })}</ul>}
    </StageCard>}

    {stage >= 3 && <StageCard key="facts" index={3} title="Facts: computed from approved records" state={state(3)}>
      {manualStep("analyze", "Set the supervisor criticality policy for this review.") || <div className="grid gap-3 sm:grid-cols-3">
        <ConsoleField label="Critical component" value={SCENARIO.criticality.component} typing={typingNow("analyze")} speed={speed} />
        <ConsoleField label="Criticality multiplier" value={String(SCENARIO.criticality.value)} typing={typingNow("analyze")} speed={speed} />
        <ConsoleField label="Criticality reason" value={SCENARIO.criticality.reason} typing={typingNow("analyze")} speed={speed} />
      </div>}
      {run.snapshot && <>
        <Note>Snapshot <span className="font-mono">{run.snapshot.snapshot_id}</span> · {run.snapshot.entries.length} approved records. Priority is a rule-based historical ordering, not a failure probability.</Note>
        <div className="overflow-x-auto rounded-lg border border-line"><table className="w-full text-left text-sm">
          <thead className="bg-bg text-xs text-fg-3"><tr>{["Fact", "Scope", "Value", "Source records"].map(label => <th key={label} className="p-2 font-medium">{label}</th>)}</tr></thead>
          <tbody>{run.facts.map(fact => <tr key={fact.fact_id} className="border-t border-line align-top">
            <td className="p-2"><Ref id={fact.fact_id} inspect={inspect} /><p className="mt-1 text-xs text-fg-3">{fact.kind}</p></td>
            <td className="p-2 text-xs">{Object.values(fact.scope).join(" · ")}</td>
            <td className="p-2 whitespace-nowrap">{fact.status === "computed" ? `${fact.value} ${fact.unit}` : "Not computed"}</td>
            <td className="p-2"><div className="flex flex-wrap gap-1">{fact.record_ids.map(id => <Ref key={id} id={id} inspect={inspect} />)}</div></td>
          </tr>)}</tbody>
        </table></div>
        {run.alerts.map(alert => <div key={String(alert.alert_id)} className="rounded-lg border-l-2 border-warn bg-warn/10 p-3 text-sm"><span className="font-medium text-warn">{String(alert.type).replace(/_/g, " ")}</span> · {String(alert.component)}<p className="text-fg-2">{String(alert.message)}</p></div>)}
      </>}
    </StageCard>}

    {stage >= 4 && <StageCard key="evidence" index={4} title="Evidence: applicable passages and cited explanation" state={state(4)}>
      {manualStep("context", "Scope the evidence search to the approved asset and component.") || <div className="grid gap-3 sm:grid-cols-3">
        <ConsoleField label="Evidence asset" value={assetOf(run)} typing={typingNow("context")} speed={speed} />
        <ConsoleField label="Evidence component" value={SCENARIO.component} typing={typingNow("context")} speed={speed} />
        <ConsoleField label="Evidence query" value={SCENARIO.query} typing={typingNow("context")} speed={speed} />
      </div>}
      {run.context?.pack && <>
        <Note>{run.context.pack.passages.length} applicable passages from {run.context.corpus_mode} corpus {run.context.pack.corpus_version}. Sources off the reviewed asset path are excluded.</Note>
        {run.context.pack.passages.map(passage => <article key={passage.passage_id} className="space-y-1.5 rounded-lg border border-line p-3">
          <div className="flex flex-wrap items-center gap-2"><Ref id={passage.passage_id} inspect={inspect} /><span className="text-xs text-fg-4">{passage.document_id} · revision {passage.version} · {passage.location}</span></div>
          <p className="text-sm text-fg-2">{passage.text}</p>
        </article>)}
      </>}
      {run.context?.pack && (draft ? <div className="space-y-3 rounded-lg border border-line bg-bg p-3">
        <div className="flex flex-wrap items-center gap-2"><Badge t="info">Draft validated</Badge><span className="text-xs text-fg-4">{run.draft_result?.explanation_mode} · {run.draft_result?.model_id} · {run.draft_result?.prompt_id}</span></div>
        <h3 className="font-semibold">Hypotheses, not confirmed causes</h3>
        {draft.hypotheses.map((claim, index) => <ClaimView key={index} claim={claim} inspect={inspect} />)}
        {!!draft.alternatives.length && <><h3 className="font-semibold">Alternatives</h3>{draft.alternatives.map((claim, index) => <ClaimView key={index} claim={claim} inspect={inspect} />)}</>}
        {draft.inspection && <><h3 className="font-semibold">Inspection guidance</h3><ClaimView claim={draft.inspection} inspect={inspect} /></>}
        <Note>{draft.uncertainty}</Note>
      </div> : manualStep("generate", "The recorded cited explanation for this evidence pack is ready to replay.") || <Note>Replaying the recorded explanation for this evidence pack…</Note>)}
    </StageCard>}

    {stage >= 5 && draft && <StageCard key="expert" index={5} title="Expert signoff" state={state(5)}>
      <ExpertSignoff key={run.run_id} run={run} w={w} draft={draft} inspect={inspect} onSigned={onSigned} />
    </StageCard>}

    {stage >= 5 && <StageCard key="report" index={6} title="Report" state={state(6)}>
      <ReportView run={run} w={w} issueForm={manualStep("issue", "The backend rechecks the signed snapshot, evidence pack and draft before rendering.")} />
    </StageCard>}
  </>;
}

function ExpertSignoff({ run, w, draft, inspect, onSigned }: { run: Run; w: Controller; draft: Draft; inspect: (id: string) => void; onSigned: () => void }) {
  const [outcome, setOutcome] = useState<Outcome>("accepted");
  const [reasons, setReasons] = useState<Record<Outcome, string>>(() => Object.fromEntries(OUTCOMES.map(o => [o.id, o.reason])) as Record<Outcome, string>);
  const [note, setNote] = useState(DEFAULT_NOTE);
  const latest = run.expert_reviews.at(-1);
  const withheld = draft.hypotheses.length > 1 ? draft.hypotheses.at(-1) : undefined;
  const reason = reasons[outcome];
  const submit = () => void w.perform("Saving the expert signoff", async () => {
    const current = w.run!;
    const corrected = outcome === "corrected" ? correctedDraft(draft, note) : undefined;
    await w.select(await request<Run>(`/runs/${current.run_id}/expert-review`, { expected_revision: current.revision, decision: outcome,
      reviewer: SCENARIO.signoffReviewer, reason: `SIMULATED: ${reason}`, ...(corrected ? { corrected } : {}) }));
    onSigned();
  });
  return <>
    <Note>You act as the reviewing expert. A signoff accepts a finding for this snapshot; it does not authorize maintenance work. This demo signoff is recorded and printed as simulated, not as a real expert approval.</Note>
    <fieldset disabled={!!w.busy} className="space-y-4">
      <legend className="sr-only">Expert decision</legend>
      <div className="grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label="Expert decision">
        {OUTCOMES.map(option => <label key={option.id} className={cx("flex cursor-pointer gap-3 rounded-lg border p-3 transition-colors", outcome === option.id ? "border-accent bg-accent-soft" : "border-line hover:bg-hover")}>
          <input type="radio" name="expert-decision" value={option.id} checked={outcome === option.id} onChange={() => setOutcome(option.id)} className="mt-1 accent-[#ffc400]" />
          <span><span className="block font-medium">{option.label}</span><span className="block text-sm text-fg-3">{option.effect}</span></span>
        </label>)}
      </div>
      {outcome === "corrected" && <div className="space-y-3 rounded-lg border border-line p-3">
        <p className="text-sm text-fg-2">Your corrected finding</p>
        {draft.hypotheses.map((claim, index) => <ClaimView key={index} claim={claim} inspect={inspect} struck={claim === withheld} />)}
        <Field label="Correction note (added to the uncertainty statement)"><textarea rows={3} className={inputClass} value={note} onChange={event => setNote(event.target.value)} /></Field>
        <Note>The backend validates your corrected draft. Numbers in prose and maintenance orders such as “replace” or “must” are refused.</Note>
      </div>}
      <Field label="Expert review reason"><textarea rows={2} className={inputClass} value={reason} onChange={event => setReasons(previous => ({ ...previous, [outcome]: event.target.value }))} /></Field>
      <div className="flex flex-wrap items-center gap-3">
        <Button primary disabled={!reason.trim() || (outcome === "corrected" && !note.trim())} onClick={submit}>Sign off: {OUTCOMES.find(o => o.id === outcome)!.label.toLowerCase()}</Button>
        <span className="text-xs text-fg-4">Signed as {SCENARIO.signoffReviewer}</span>
      </div>
      {w.error && <p role="alert" className="rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm text-danger">{w.error}</p>}
    </fieldset>
    {latest && <div className={cx("rounded-lg border-l-2 p-3 text-sm", ["accepted", "corrected"].includes(latest.decision) ? "border-ok bg-ok/10" : "border-warn bg-warn/10")}>
      <p className="font-medium">Saved signoff {run.expert_reviews.length}: {latest.decision}</p>
      <p className="text-fg-2">{latest.reason}</p>
      {run.expert_reviews.length > 1 && <p className="mt-1 text-xs text-fg-4">Earlier decisions: {run.expert_reviews.slice(0, -1).map(review => review.decision).join(" → ")}</p>}
    </div>}
  </>;
}

function ReportView({ run, w, issueForm }: { run: Run; w: Controller; issueForm: ReactNode }) {
  const latest = run.expert_reviews.at(-1);
  const report = run.latest_report;
  const history = w.reports.filter(value => value.report_id !== report?.report_id);
  const tone: Tone = latest?.decision === "rejected" ? "danger" : "warn";
  return <>
    {!latest && <Note>Waiting for your signoff. The backend refuses to issue a report without a current-snapshot decision.</Note>}
    {latest && !["accepted", "corrected"].includes(latest.decision) && <div className="space-y-1 rounded-lg border border-line p-3">
      <Badge t={tone}>Report blocked</Badge>
      <p className="text-sm text-fg-2">The finding was signed off as <span className="text-fg">{latest.decision}</span>, so no report can be issued for this snapshot. Choose another decision above to continue.</p>
    </div>}
    {latest && ["accepted", "corrected"].includes(latest.decision) && !report && (issueForm || <Note>Rendering the PDF for the signed snapshot…</Note>)}
    {report && <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2"><Badge t="ok">Issued</Badge><Badge t="synthetic">Synthetic data · simulated signoff</Badge><span className="text-xs text-fg-4">Signed as {report.expert_review.decision}</span></div>
      <dl className="grid gap-2 text-sm sm:grid-cols-2">
        <div><dt className="text-fg-4">Report</dt><dd className="font-mono text-xs">{report.report_id}</dd></div>
        <div><dt className="text-fg-4">Snapshot</dt><dd className="font-mono text-xs">{report.snapshot_id}</dd></div>
        <div className="sm:col-span-2"><dt className="text-fg-4">PDF SHA-256</dt><dd className="font-mono text-xs break-all">{report.sha256}</dd></div>
      </dl>
      <div className="flex flex-wrap gap-2">
        <a className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-accent bg-accent px-3 py-2 text-sm font-medium text-on-brand hover:bg-accent-hover" href={reportUrl(run.run_id, report.report_id)} download={`${report.report_id}.pdf`}><Icon name="report" size={14} />Download PDF</a>
        <a className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-line-strong px-3 py-2 text-sm hover:bg-hover" href={reportUrl(run.run_id, report.report_id)} target="_blank" rel="noreferrer"><Icon name="external" size={14} />Open in a new tab</a>
      </div>
      <iframe title="Issued report preview" src={reportUrl(run.run_id, report.report_id)} className="hidden h-[640px] w-full rounded-lg border border-line bg-white md:block" />
    </div>}
    {!!history.length && <div className="space-y-2">
      <p className="text-sm text-fg-3">Earlier PDFs stay tied to their original signoff</p>
      {history.map(value => <a key={value.report_id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line p-2 text-sm hover:bg-hover" href={reportUrl(run.run_id, value.report_id)} download={`${value.report_id}.pdf`}>
        <span className="font-mono text-xs">{value.report_id}</span><span className="text-xs text-fg-3">Historical · signed {value.expert_review.decision}</span></a>)}
    </div>}
  </>;
}
