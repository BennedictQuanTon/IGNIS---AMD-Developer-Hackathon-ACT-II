import { useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Icon } from "../components/ui/icons";
import { EASE } from "../components/ui/motion";
import { Badge, cx, type Tone } from "../components/ui/primitives";
import {
  alert,
  claims,
  columns,
  draft,
  excluded,
  facts,
  passages,
  records,
  rowIssues,
  run,
  type RecordState,
  type SpanType,
  type WorkOrder,
} from "./mock";
import type { Decision } from "./Workspace";

export type Selection =
  | { kind: "record" | "fact" | "passage" | "column" | "ref"; id: string }
  | null;

export type ExpertDecision = { outcome: "accept" | "correct" | "reject" | "inconclusive"; reason: string };

type Select = (s: Selection) => void;

/* Shared pieces -------------------------------------------------------------- */

function ScreenHeader({ title, desc, children }: { title: string; desc: string; children?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-[32px] leading-[1.15] font-semibold tracking-[-0.02em] text-fg">{title}</h1>
        <p className="mt-2 max-w-xl text-[14px] leading-[1.55] text-fg-3">{desc}</p>
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  );
}

function Panel({ title, aside, children, className }: { title?: string; aside?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cx("rounded-[var(--radius-lg)] border border-line bg-elevated", className)}>
      {title && (
        <div className="flex h-12 items-center justify-between gap-3 border-b border-line px-4">
          <h2 className="text-[15px] leading-[1.4] font-semibold text-fg">{title}</h2>
          {aside}
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

function Btn({
  children,
  onClick,
  variant = "secondary",
  disabled,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "danger";
  disabled?: boolean;
}) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      disabled={disabled}
      whileTap={disabled ? undefined : { scale: 0.97 }}
      className={cx(
        "inline-flex h-8 items-center gap-1.5 rounded-[var(--radius)] px-3 text-[13px] font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40",
        variant === "primary" && "bg-accent text-on-brand hover:bg-accent-hover",
        variant === "secondary" && "border border-line-strong text-fg hover:bg-hover",
        variant === "danger" && "border border-danger/40 text-danger hover:bg-danger/10",
      )}
    >
      {children}
    </motion.button>
  );
}

function Blocked({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-3 rounded-[var(--radius-lg)] border border-dashed border-line-strong p-5 text-[13px] text-fg-2">
      <Icon name="alert" className="mt-0.5 shrink-0 text-warn" />
      <div>
        <p className="font-semibold text-fg">Blocked</p>
        <p className="mt-1 text-fg-3">{children}</p>
      </div>
    </div>
  );
}

function IdChip({ id, kind, select }: { id: string; kind: NonNullable<Selection>["kind"]; select: Select }) {
  return (
    <button
      type="button"
      onClick={() => select({ kind, id })}
      className="rounded-[4px] border border-line-strong bg-bg px-1.5 py-px font-mono text-[11px] text-fg-2 transition-colors hover:border-accent/50 hover:text-brand-text"
    >
      {id}
    </button>
  );
}

const spanStyle: Record<SpanType, string> = {
  component: "bg-info/12 decoration-info",
  fault: "bg-danger/12 decoration-danger",
  action: "bg-ok/12 decoration-ok",
};

export function SpanText({ record }: { record: WorkOrder }) {
  const out: ReactNode[] = [];
  let cursor = 0;
  for (const s of record.spans) {
    if (s.start > cursor) out.push(record.text.slice(cursor, s.start));
    out.push(
      <span key={s.start} className="inline-flex flex-col items-start align-bottom">
        <span className="font-mono text-[10px] leading-4 text-fg-3">{s.type}</span>
        <span className={cx("rounded-[3px] px-0.5 underline decoration-2 underline-offset-4", spanStyle[s.type])}>
          {record.text.slice(s.start, s.end)}
        </span>
      </span>,
    );
    cursor = s.end;
  }
  if (cursor < record.text.length) out.push(record.text.slice(cursor));
  return <p className="text-[16px] leading-[1.9] whitespace-pre-wrap text-fg">{out}</p>;
}

/* 1 Source ------------------------------------------------------------------------ */

export function SourceScreen({ onNext, select }: { onNext: () => void; select: Select }) {
  return (
    <>
      <ScreenHeader title="Source" desc="Original rows are kept unmodified.">
        <Btn variant="primary" onClick={onNext}>
          Continue to mapping <Icon name="arrow" size={14} />
        </Btn>
      </ScreenHeader>
      <div className="grid gap-4">
        <Panel title="File">
          <dl className="grid grid-cols-2 gap-4 text-[13px] sm:grid-cols-4">
            {[
              ["File", run.file],
              ["Hash", run.hash],
              ["Parser", run.parser],
              ["Rows read", `${run.rows} · ${run.issues} issue`],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="text-[12px] text-fg-4">{k}</dt>
                <dd className="mt-1 truncate font-mono text-[12px] text-fg-2">{v}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-4 rounded-[var(--radius)] border border-dashed border-line-strong p-4 text-center text-[12px] text-fg-3">
            Synthetic fixture loaded · file upload is not connected in this preview
          </div>
        </Panel>
        <Panel title="Rows">
          <div className="scrollbar-thin overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-[13px]">
              <thead className="text-[12px] text-fg-4">
                <tr className="border-b border-line">
                  <th className="py-2 pr-3 font-medium">Row</th>
                  {columns.map((c) => (
                    <th key={c.source} className="py-2 pr-3 font-medium">
                      {c.source}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr
                    key={r.id}
                    onClick={() => select({ kind: "record", id: r.id })}
                    className="cursor-pointer border-b border-line last:border-0 hover:bg-hover"
                  >
                    <td className="h-9 pr-3 font-mono text-[12px] text-fg-4">{r.row}</td>
                    <td className="h-9 pr-3 text-fg-2">{r.text}</td>
                    <td className="h-9 pr-3 font-mono text-[12px] text-fg-2">{r.asset}</td>
                    <td className="h-9 pr-3 font-mono text-[12px] text-fg-3">2026-0{r.row}-14</td>
                    <td className={cx("py-2 pr-3 font-mono text-[12px]", r.row === 5 ? "text-danger" : "text-fg-3")}>
                      {r.row === 5 ? "-3" : "4.5"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
        <ValidationIssues />
      </div>
    </>
  );
}

function ValidationIssues() {
  return (
    <div className="rounded-[var(--radius-lg)] border border-line border-l-2 border-l-warn bg-elevated p-4">
      <p className="text-[15px] font-semibold text-fg">Validation issues</p>
      <ul className="mt-2 space-y-1 text-[13px] text-fg-2">
        {rowIssues.map((i) => (
          <li key={i.row}>
            <span className="font-mono text-[12px] text-fg-3">
              row {i.row} · {i.column}
            </span>{" "}
            — {i.message}
          </li>
        ))}
      </ul>
    </div>
  );
}

/* 2 Mapping ------------------------------------------------------------------------ */

export function MappingScreen({
  confirmed,
  onConfirm,
  onNext,
  select,
}: {
  confirmed: boolean;
  onConfirm: () => void;
  onNext: () => void;
  select: Select;
}) {
  return (
    <>
      <ScreenHeader title="Mapping" desc="Matches stay proposed until you confirm them.">
        {confirmed ? (
          <Btn variant="primary" onClick={onNext}>
            Continue to review <Icon name="arrow" size={14} />
          </Btn>
        ) : (
          <Btn variant="primary" onClick={onConfirm}>
            <Icon name="check" size={14} /> Confirm mapping
          </Btn>
        )}
      </ScreenHeader>
      <Panel
        title="Columns"
        aside={
          <AnimatePresence mode="wait" initial={false}>
            <motion.span key={String(confirmed)} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}>
              {confirmed ? <Badge t="ok">Confirmed</Badge> : <Badge t="warn">Proposed</Badge>}
            </motion.span>
          </AnimatePresence>
        }
      >
        <ul className="divide-y divide-line">
          {columns.map((c, i) => (
            <motion.li
              key={c.source}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.4, ease: EASE }}
              className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 py-3 sm:grid-cols-[1fr_auto_1fr_auto]"
            >
              <button type="button" onClick={() => select({ kind: "column", id: c.source })} className="text-left">
                <div className="text-[13px] text-fg">{c.source}</div>
                <div className="truncate font-mono text-[12px] text-fg-4">{c.sample}</div>
              </button>
              <Icon name="arrow" className="text-fg-4" />
              <div className="text-[13px] text-fg-2">{c.target}</div>
              <div className="col-span-3 sm:col-span-1">
                <Badge t={confirmed ? "ok" : "plain"} dot={false} mono>
                  {c.rule}
                </Badge>
              </div>
            </motion.li>
          ))}
        </ul>
      </Panel>
      <div className="mt-4">
        <ValidationIssues />
      </div>
    </>
  );
}

/* 3 Review ------------------------------------------------------------------------- */

const stateTone: Record<RecordState, Tone> = {
  pending: "warn",
  approved: "ok",
  corrected: "info",
  rejected: "danger",
};

const stateDot: Record<RecordState, string> = {
  pending: "bg-warn",
  approved: "bg-ok",
  corrected: "bg-info",
  rejected: "bg-danger",
};

export function ReviewScreen({
  blocked,
  decisions,
  onDecide,
  onNext,
  select,
}: {
  blocked: boolean;
  decisions: Record<string, Decision>;
  onDecide: (id: string, state: RecordState, reason: string) => void;
  onNext: () => void;
  select: Select;
}) {
  const [index, setIndex] = useState(0);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const record = records[index];
  const decision = decisions[record.id];

  const counts = (["pending", "approved", "corrected", "rejected"] as RecordState[]).map((s) => ({
    s,
    n: Object.values(decisions).filter((d) => d.state === s).length,
  }));

  if (blocked)
    return (
      <>
        <ScreenHeader title="Annotation review" desc="Accept, correct or reject each suggestion." />
        <Blocked>Confirm the column mapping before reviewing annotations.</Blocked>
      </>
    );

  const decide = (state: RecordState) => {
    if (!reason.trim()) {
      setError("A reason is required for every review decision.");
      return;
    }
    setError(null);
    onDecide(record.id, state, reason.trim());
    setReason("");
    const nextPending = records.findIndex((r, i) => i > index && decisions[r.id].state === "pending");
    if (nextPending >= 0) setIndex(nextPending);
  };

  return (
    <>
      <ScreenHeader title="Annotation review" desc="Only approved and corrected records count.">
        <Btn variant="primary" onClick={onNext}>
          Continue to facts <Icon name="arrow" size={14} />
        </Btn>
      </ScreenHeader>

      <div className="mb-4 flex flex-wrap gap-2">
        {counts.map(({ s, n }) => (
          <Badge key={s} t={stateTone[s]}>
            <span className="capitalize">{s}</span> <span className="tabular-nums">{n}</span>
          </Badge>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[200px_1fr]">
        <ul className="scrollbar-thin flex gap-1 overflow-x-auto lg:flex-col lg:overflow-visible">
          {records.map((r, i) => (
            <li key={r.id}>
              <button
                type="button"
                onClick={() => {
                  setIndex(i);
                  setError(null);
                }}
                className={cx(
                  "flex w-full items-center justify-between gap-2 rounded-[6px] px-2.5 py-2 text-left whitespace-nowrap transition-colors",
                  i === index ? "bg-hover text-fg" : "text-fg-2 hover:bg-hover/60",
                )}
              >
                <span className="font-mono text-[12px]">{r.id}</span>
                <span className={cx("size-1.5 rounded-full", stateDot[decisions[r.id].state])} />
              </button>
            </li>
          ))}
        </ul>

        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={record.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25, ease: EASE }}
            className="grid gap-4"
          >
            <Panel
              title={`Record ${record.id}`}
              aside={
                <div className="flex items-center gap-2">
                  <span className="hidden font-mono text-[12px] text-fg-4 sm:inline">row {record.row}</span>
                  <Badge t={stateTone[decision.state]}>
                    <span className="capitalize">{decision.state}</span>
                  </Badge>
                </div>
              }
            >
                            {record.invalidOutput ? (
                <>
                  <p className="text-[16px] text-fg">{record.text}</p>
                  <div className="mt-4 rounded-[var(--radius)] border border-line border-l-2 border-l-danger bg-bg p-3 text-[13px]">
                    <p className="font-medium text-danger">Invalid model output</p>
                    <p className="mt-1 text-fg-2">{record.invalidOutput}</p>
                  </div>
                </>
              ) : (
                <SpanText record={record} />
              )}
              <div className="mt-5 flex flex-wrap gap-3 text-[11px] text-fg-3">
                {(["component", "fault", "action"] as SpanType[]).map((t) => (
                  <span key={t} className="flex items-center gap-1.5">
                    <span className={cx("h-0.5 w-4 rounded-full", { component: "bg-info", fault: "bg-danger", action: "bg-ok" }[t])} />
                    {t}
                  </span>
                ))}
              </div>
            </Panel>

            {!record.invalidOutput && (
              <Panel title="Suggestions">
                <table className="w-full text-left text-[13px]">
                  <thead className="text-[12px] text-fg-4">
                    <tr>
                      <th className="pb-2 font-medium">Entity</th>
                      <th className="pb-2 font-medium">Type</th>
                      <th className="pb-2 font-medium">Span</th>
                      <th className="pb-2 font-medium">Validity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {record.spans.map((s) => (
                      <tr key={s.start} className="border-t border-line">
                        <td className="h-9 text-fg">{record.text.slice(s.start, s.end)}</td>
                        <td className="h-9 text-fg-2">{s.type}</td>
                        <td className="h-9 font-mono text-[12px] text-fg-3">
                          {s.start}–{s.end}
                        </td>
                        <td className="py-2">
                          <Badge t="ok">valid</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Panel>
            )}

            <Panel title="Decision">
              <label htmlFor="reason" className="text-[12px] text-fg-3">
                Reason
              </label>
              <input
                id="reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                aria-invalid={!!error}
                aria-describedby={error ? "reason-error" : undefined}
                placeholder="Required for every decision"
                className="mt-1.5 h-9 w-full rounded-[var(--radius)] border border-line-strong bg-bg px-3 text-[13px] text-fg placeholder:text-fg-4 focus:border-accent/60 focus:outline-none"
              />
              <p id="reason-error" aria-live="polite" className="mt-1.5 min-h-4 text-[12px] text-danger">
                {error}
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Btn variant="primary" onClick={() => decide("approved")} disabled={!!record.invalidOutput}>
                  <Icon name="check" size={14} /> Accept
                </Btn>
                <Btn onClick={() => decide("corrected")}>{record.invalidOutput ? "Annotate manually" : "Correct"}</Btn>
                <Btn variant="danger" onClick={() => decide("rejected")}>
                  Reject
                </Btn>
                <button
                  type="button"
                  onClick={() => select({ kind: "record", id: record.id })}
                  className="ml-auto text-[12px] text-fg-3 hover:text-fg"
                >
                  Inspect provenance →
                </button>
              </div>
              {decision.revision > 0 && (
                <p className="mt-4 border-t border-line pt-3 font-mono text-[11px] text-fg-3">
                  rev {decision.revision} · {decision.state}
                  {decision.reason && ` · “${decision.reason}”`}
                </p>
              )}
            </Panel>
          </motion.div>
        </AnimatePresence>
      </div>
    </>
  );
}

/* 4 Facts & alerts ----------------------------------------------------------------- */

export function FactsScreen({
  blocked,
  approved,
  pending,
  onNext,
  select,
}: {
  blocked: boolean;
  approved: number;
  pending: number;
  onNext: () => void;
  select: Select;
}) {
  if (blocked)
    return (
      <>
        <ScreenHeader title="Facts & alerts" desc="Code computes every number from the approved snapshot." />
        <Blocked>Approve or correct at least one record to build a snapshot.</Blocked>
      </>
    );
  const bandTone: Record<string, Tone> = { High: "accent", Medium: "warn", Low: "plain" };
  return (
    <>
      <ScreenHeader title="Facts & alerts" desc="Computed by code from the approved snapshot.">
        <Btn variant="primary" onClick={onNext}>
          Investigate evidence <Icon name="arrow" size={14} />
        </Btn>
      </ScreenHeader>
      <div className="mb-4 flex flex-wrap gap-2 font-mono text-[11px] text-fg-3">
        <span className="rounded-[4px] border border-line px-2 py-1">snapshot snap_mock_02</span>
        <span className="rounded-[4px] border border-line px-2 py-1">approved {approved}</span>
        <span className="rounded-[4px] border border-line px-2 py-1">excluded / pending {6 - approved}</span>
              </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: EASE }}
        className="relative mb-4 overflow-hidden rounded-[var(--radius-lg)] border border-accent/40 bg-accent-soft p-4"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-accent opacity-60" />
              <span className="relative inline-flex size-2 rounded-full bg-accent" />
            </span>
            <span className="font-mono text-[12px] text-brand-text">{alert.id}</span>
            <span className="text-[13px] font-medium text-fg">
              {alert.kind} · {alert.component}
            </span>
          </div>
          <IdChip id="F-01" kind="fact" select={select} />
        </div>
        <p className="mt-2 text-[13px] text-fg-2">Trigger: {alert.rule}</p>
      </motion.div>

      <Panel title="Component priority" aside={pending > 0 ? <Badge t="warn">{pending} pending excluded</Badge> : undefined}>
        <div className="scrollbar-thin overflow-x-auto">
          <table className="w-full min-w-[620px] text-left text-[13px]">
            <thead className="text-[12px] text-fg-4">
              <tr>
                {["Fact", "Component", "Severity", "Recurrence", "Criticality", "Priority", "Band"].map((h) => (
                  <th key={h} className="pb-2 font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {facts.map((f, i) => (
                <motion.tr
                  key={f.id}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 + i * 0.05, duration: 0.4, ease: EASE }}
                  className="border-t border-line"
                >
                  <td className="h-9">
                    <IdChip id={f.id} kind="fact" select={select} />
                  </td>
                  <td className="py-2.5 text-fg">{f.component}</td>
                  <td className="py-2.5 font-mono text-fg-2">{f.severity ?? <NotComputed />}</td>
                  <td className="py-2.5 font-mono text-fg-2">{f.recurrence}</td>
                  <td className="py-2.5 font-mono text-fg-2">{f.criticality}</td>
                  <td className="py-2.5 font-mono text-fg">{f.priority ?? <NotComputed />}</td>
                  <td className="h-9">{f.band ? <Badge t={bandTone[f.band]}>{f.band}</Badge> : <NotComputed />}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-[12px] text-fg-3">
          Priority is a rule-based ordering, not a failure probability.
        </p>
      </Panel>
    </>
  );
}

function NotComputed() {
  return <span className="text-[12px] text-fg-4">Not computed – severity missing</span>;
}

/* 5 Evidence & expert review ------------------------------------------------------- */

export function EvidenceScreen({
  blocked,
  expert,
  onDecide,
  onNext,
  select,
}: {
  blocked: boolean;
  expert: ExpertDecision | null;
  onDecide: (d: ExpertDecision) => void;
  onNext: () => void;
  select: Select;
}) {
  const [reason, setReason] = useState("");
  if (blocked)
    return (
      <>
        <ScreenHeader title="Evidence & expert review" desc="Applicable evidence and a cited draft for the active alert." />
        <Blocked>No approved snapshot yet, so no evidence pack can be built.</Blocked>
      </>
    );
  const outcomes: { o: ExpertDecision["outcome"]; label: string; v: "primary" | "secondary" | "danger" }[] = [
    { o: "accept", label: "Accept finding", v: "primary" },
    { o: "correct", label: "Correct", v: "secondary" },
    { o: "reject", label: "Reject", v: "danger" },
    { o: "inconclusive", label: "Inconclusive", v: "secondary" },
  ];
  return (
    <>
      <ScreenHeader title="Evidence & expert review" desc="The model drafts. The expert decides.">
        <Btn variant="primary" onClick={onNext} disabled={!expert}>
          Continue to report <Icon name="arrow" size={14} />
        </Btn>
      </ScreenHeader>
      <div className="mb-4 flex flex-wrap gap-2 font-mono text-[11px] text-fg-3">
        <span className="rounded-[4px] border border-line px-2 py-1">alert {alert.id}</span>
        <span className="rounded-[4px] border border-line px-2 py-1">snapshot {alert.snapshot}</span>
        <span className="rounded-[4px] border border-line px-2 py-1">pack ep_mock_01</span>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Panel title="Trusted facts">
          <div className="flex items-start gap-2 text-[13px]">
            <IdChip id="F-01" kind="fact" select={select} />
            <span className="text-fg-2">seal · P-101 — priority 6, band High, recurrence 2</span>
          </div>
        </Panel>
        <Panel title="Applicable evidence" aside={<span className="font-mono text-[12px] text-fg-4">top {passages.length} of 3</span>}>
          <ul className="space-y-3">
            {passages.map((p) => (
              <li key={p.id} className="text-[13px]">
                <div className="flex items-center gap-2">
                  <IdChip id={p.id} kind="passage" select={select} />
                  <span className="text-fg-3">{p.source}</span>
                </div>
                <p className="mt-1 text-fg-2">{p.text}</p>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <details className="group mt-4 rounded-[var(--radius-lg)] border border-line bg-elevated">
        <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-[13px] font-semibold text-fg">
          Excluded sources ({excluded.length})
          <span className="text-fg-4 transition-transform group-open:rotate-90">›</span>
        </summary>
        <ul className="space-y-1.5 border-t border-line p-4 text-[13px]">
          {excluded.map((e) => (
            <li key={e.source} className="flex flex-wrap gap-x-2">
              <span className="text-fg-3 line-through decoration-fg-4">{e.source}</span>
              <span className="text-fg-2">— {e.reason}</span>
            </li>
          ))}
        </ul>
      </details>

      <section className="mt-4 rounded-[var(--radius-lg)] border border-dashed border-line-strong bg-elevated p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Badge t="info">{draft.status} · hypothesis</Badge>
          
        </div>
        <p className="mt-3 text-[15px] leading-relaxed text-fg">{draft.hypothesis}</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {draft.facts.map((id) => (
            <IdChip key={id} id={id} kind="fact" select={select} />
          ))}
          {draft.passages.map((id) => (
            <IdChip key={id} id={id} kind="passage" select={select} />
          ))}
        </div>
        <dl className="mt-4 grid gap-3 text-[13px] sm:grid-cols-2">
          <div>
            <dt className="text-[12px] text-fg-4">Alternatives</dt>
            <dd className="mt-1 text-fg-2">{draft.alternatives.join("; ")}</dd>
          </div>
          <div>
            <dt className="text-[12px] text-fg-4">Uncertainty</dt>
            <dd className="mt-1 text-fg-2">{draft.uncertainty}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-[12px] text-fg-4">Suggested inspection (not authorised)</dt>
            <dd className="mt-1 text-fg-2">{draft.inspection}</dd>
          </div>
        </dl>
        <ul className="mt-4 flex flex-wrap gap-1.5">
          {draft.checks.map((c) => (
            <li key={c}>
              <Badge t="ok">{c}</Badge>
            </li>
          ))}
        </ul>
      </section>

      <Panel title="Expert decision" className="mt-4">
        <label htmlFor="expert-reason" className="text-[12px] text-fg-3">
          Reason
        </label>
        <input
          id="expert-reason"
          aria-required="true"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Required: evidence you relied on"
          className="mt-1.5 h-9 w-full rounded-[var(--radius)] border border-line-strong bg-bg px-3 text-[13px] text-fg placeholder:text-fg-4 focus:border-accent/60 focus:outline-none"
        />
        <div className="mt-3 flex flex-wrap gap-2">
          {outcomes.map(({ o, label, v }) => (
            <Btn key={o} variant={v} disabled={!reason.trim()} onClick={() => onDecide({ outcome: o, reason: reason.trim() })}>
              {label}
            </Btn>
          ))}
        </div>
        <AnimatePresence>
          {expert && (
            <motion.p
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-3 overflow-hidden font-mono text-[11px] text-fg-3"
            >
              Saved · {expert.outcome}{expert.reason && ` · “${expert.reason}”`}
            </motion.p>
          )}
        </AnimatePresence>
      </Panel>
    </>
  );
}

/* 6 Report -------------------------------------------------------------------------- */

export function ReportScreen({
  blocked,
  issued,
  onIssue,
  select,
}: {
  blocked: boolean;
  issued: boolean;
  onIssue: () => void;
  select: Select;
}) {
  return (
    <>
      <ScreenHeader title="Report" desc="Issued from pinned facts and reviewed findings.">
        <Btn variant="primary" onClick={onIssue} disabled={blocked || issued}>
          Generate approved report
        </Btn>
      </ScreenHeader>
      {blocked && (
        <div className="mb-4">
          <Blocked>Accept or correct the finding first.</Blocked>
        </div>
      )}
      <Panel
        title="Preview"
        aside={
          <AnimatePresence mode="wait" initial={false}>
            <motion.span key={String(issued)} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
              {issued ? <Badge t="ok">Approved</Badge> : <Badge t="warn">Draft</Badge>}
            </motion.span>
          </AnimatePresence>
        }
      >
        <ol className="space-y-3">
          {claims.map((c, i) => (
            <li key={i} className="flex flex-wrap items-start gap-x-3 gap-y-1.5 border-b border-line pb-3 last:border-0 last:pb-0">
              <span className="font-mono text-[12px] text-fg-4">C{i + 1}</span>
              <span className="flex-1 text-[14px] text-fg">{c.text}</span>
              <span className="flex gap-1">
                {c.refs.map((r) => (
                  <IdChip key={r} id={r} kind="ref" select={select} />
                ))}
              </span>
            </li>
          ))}
        </ol>
      </Panel>
      <Panel title="Output history" className="mt-4">
        {issued ? (
          <p className="font-mono text-[12px] text-fg-2">v1 · ep_mock_01</p>
        ) : (
          <p className="text-[14px] text-fg-3">No report issued yet.</p>
        )}
      </Panel>
    </>
  );
}
