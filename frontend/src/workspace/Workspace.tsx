import { useMemo, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Icon } from "../components/ui/icons";
import { EASE } from "../components/ui/motion";
import { Badge, cx, Wordmark, type Tone } from "../components/ui/primitives";
import { records, run, type RecordState } from "./mock";
import {
  EvidenceScreen,
  FactsScreen,
  MappingScreen,
  ReportScreen,
  ReviewScreen,
  SourceScreen,
  type ExpertDecision,
  type Selection,
} from "./screens";
import { Inspector } from "./Inspector";


type StageStatus = "done" | "active" | "blocked" | "todo";

const STAGES = ["Source", "Mapping", "Review", "Facts", "Evidence", "Report"] as const;

export type Decision = { state: RecordState; reason: string; revision: number };

export function Workspace({ embedded = false }: { embedded?: boolean }) {
  const [stage, setStage] = useState(0);
  const [direction, setDirection] = useState(1);
  const [mappingConfirmed, setMappingConfirmed] = useState(false);
  const [decisions, setDecisions] = useState<Record<string, Decision>>(() =>
    Object.fromEntries(records.map((r) => [r.id, { state: "pending" as RecordState, reason: "", revision: 0 }])),
  );
  const [expert, setExpert] = useState<ExpertDecision | null>(null);
  const [reportIssued, setReportIssued] = useState(false);
  const [selection, setSelection] = useState<Selection>(null);
  const [drawer, setDrawer] = useState(false);

  const approvedCount = Object.values(decisions).filter((d) => d.state === "approved" || d.state === "corrected").length;
  const pendingCount = Object.values(decisions).filter((d) => d.state === "pending").length;
  const expertOk = expert?.outcome === "accept" || expert?.outcome === "correct";

  const statuses: StageStatus[] = useMemo(
    () => [
      "done",
      mappingConfirmed ? "done" : "todo",
      !mappingConfirmed ? "blocked" : pendingCount === 0 ? "done" : "todo",
      approvedCount === 0 ? "blocked" : "done",
      approvedCount === 0 ? "blocked" : expert ? "done" : "todo",
      !expertOk ? "blocked" : reportIssued ? "done" : "todo",
    ],
    [mappingConfirmed, pendingCount, approvedCount, expert, expertOk, reportIssued],
  );

  const mainRef = useRef<HTMLElement>(null);

  const go = (next: number) => {
    mainRef.current?.scrollTo({ top: 0 });
    setDirection(next > stage ? 1 : -1);
    setStage(next);
    setSelection(null);
  };

  const select = (s: Selection) => {
    setSelection(s);
    setDrawer(true);
  };

  const screens: ReactNode[] = [
    <SourceScreen onNext={() => go(1)} select={select} />,
    <MappingScreen
      confirmed={mappingConfirmed}
      onConfirm={() => setMappingConfirmed(true)}
      onNext={() => go(2)}
      select={select}
    />,
    <ReviewScreen
      blocked={!mappingConfirmed}
      decisions={decisions}
      onDecide={(id, state, reason) => {
        setDecisions((d) => ({ ...d, [id]: { state, reason, revision: d[id].revision + 1 } }));
        setExpert(null);
        setReportIssued(false);
      }}
      onNext={() => go(3)}
      select={select}
    />,
    <FactsScreen blocked={approvedCount === 0} approved={approvedCount} pending={pendingCount} onNext={() => go(4)} select={select} />,
    <EvidenceScreen blocked={approvedCount === 0} expert={expert} onDecide={(decision) => { setExpert(decision); setReportIssued(false); }} onNext={() => go(5)} select={select} />,
    <ReportScreen blocked={!expertOk} issued={reportIssued} onIssue={() => setReportIssued(true)} select={select} />,
  ];

  return (
    <div className={cx("relative flex flex-col bg-bg text-[14px] tracking-normal text-fg", embedded ? "h-full" : "h-dvh")}>
      {/* Top bar */}
      <header className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-line bg-elevated px-4">
        <a href="#/" aria-label="Back to landing page" className="flex items-center">
          <Wordmark height={15} />
        </a>
        <div className="flex items-center gap-2">
          <Badge t="warn">Mock data</Badge>
          <button
            type="button"
            onClick={() => setDrawer((v) => !v)}
            className="grid size-8 place-items-center rounded-[var(--radius)] text-fg-3 hover:bg-hover hover:text-fg xl:hidden"
            aria-label="Toggle evidence inspector"
            aria-expanded={drawer}
          >
            <Icon name="panel" />
          </button>
        </div>
      </header>

      {/* Stepper */}
      <nav aria-label="Workflow stages" className="scrollbar-thin overflow-x-auto border-b border-line px-2 lg:hidden">
        <ol className="flex min-w-max items-center">
          {STAGES.map((name, i) => (
            <li key={name} className="relative">
              <button
                type="button"
                onClick={() => go(i)}
                aria-current={stage === i ? "step" : undefined}
                className={cx(
                  "relative flex h-11 items-center gap-2 px-3 text-[13px] transition-colors",
                  stage === i ? "text-fg" : "text-fg-3 hover:text-fg-2",
                )}
              >
                <StageDot status={statuses[i]} index={i} />
                {name}
                <span className="sr-only">({statuses[i]})</span>
              </button>
              {stage === i && (
                <motion.span
                  layoutId="stage-underline"
                  className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-accent"
                  transition={{ type: "spring", stiffness: 420, damping: 36 }}
                />
              )}
            </li>
          ))}
        </ol>
      </nav>

      {/* Body */}
      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-60 shrink-0 flex-col border-r border-line bg-elevated p-3 lg:flex" aria-label="Workflow stages">
          <div className="px-2 py-1.5">
            <div className="truncate text-[13px] text-fg">{run.file}</div>
            <div className="mt-0.5 font-mono text-[12px] text-fg-4">{run.hash}</div>
          </div>
          <ul className="mt-3 space-y-0.5">
            {STAGES.map((name, i) => (
              <li key={name} className="relative">
                {stage === i && (
                  <motion.span
                    layoutId="stage-active"
                    className="absolute inset-0 rounded-[6px] bg-hover"
                    transition={{ type: "spring", stiffness: 420, damping: 36 }}
                  />
                )}
                <button
                  type="button"
                  onClick={() => go(i)}
                  aria-current={stage === i ? "step" : undefined}
                  className={cx(
                    "relative flex h-9 w-full items-center gap-2.5 rounded-[6px] px-2 text-left text-[13px] transition-colors",
                    stage === i ? "text-fg" : "text-fg-2 hover:text-fg",
                  )}
                >
                  <StageDot status={statuses[i]} index={i} />
                  {name}
                  <span className="sr-only">({statuses[i]})</span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <main ref={mainRef} className="relative min-w-0 flex-1 overflow-y-auto scrollbar-thin">
          <AnimatePresence mode="wait" custom={direction} initial={false}>
            <motion.div
              key={stage}
              custom={direction}
              variants={{
                enter: (d: number) => ({ opacity: 0, x: 24 * d, filter: "blur(4px)" }),
                center: { opacity: 1, x: 0, filter: "blur(0px)" },
                exit: (d: number) => ({ opacity: 0, x: -24 * d, filter: "blur(4px)" }),
              }}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.35, ease: EASE }}
              className="mx-auto max-w-[920px] p-4 sm:p-6"
            >
              {screens[stage]}
            </motion.div>
          </AnimatePresence>
        </main>

        {/* Inspector: fixed column on xl, drawer below */}
        <aside className="hidden w-[360px] shrink-0 border-l border-line bg-elevated xl:block">
          <Inspector selection={selection} decisions={decisions} />
        </aside>
        <AnimatePresence>
          {drawer && (
            <>
              <motion.div
                className={cx(embedded ? "absolute" : "fixed", "inset-0 z-40 bg-black/50 xl:hidden")}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setDrawer(false)}
              />
              <motion.aside
                role="dialog"
                aria-label="Evidence inspector"
                className={cx(embedded ? "absolute" : "fixed", "inset-y-0 right-0 z-50 w-[min(360px,92vw)] border-l border-line bg-elevated shadow-2xl xl:hidden")}
                initial={{ x: "100%" }}
                animate={{ x: 0 }}
                exit={{ x: "100%" }}
                transition={{ duration: 0.4, ease: EASE }}
              >
                <button
                  type="button"
                  onClick={() => setDrawer(false)}
                  className="absolute top-3 right-3 grid size-8 place-items-center rounded-[var(--radius)] text-fg-3 hover:bg-hover"
                  aria-label="Close inspector"
                >
                  <Icon name="close" />
                </button>
                <Inspector selection={selection} decisions={decisions} />
              </motion.aside>
            </>
          )}
        </AnimatePresence>
      </div>

    </div>
  );
}

function StageDot({ status, index }: { status: StageStatus; index: number }) {
  const map: Record<StageStatus, { cls: string; t: Tone }> = {
    done: { cls: "border-ok/50 bg-ok/15 text-ok", t: "ok" },
    active: { cls: "border-accent text-brand-text", t: "accent" },
    todo: { cls: "border-line-strong text-fg-3", t: "plain" },
    blocked: { cls: "border-dashed border-line-strong text-fg-4", t: "neutral" },
  };
  return (
    <span className={cx("grid size-5 place-items-center rounded-full border font-mono text-[10px]", map[status].cls)}>
      {status === "done" ? <Icon name="check" size={10} /> : index + 1}
    </span>
  );
}
