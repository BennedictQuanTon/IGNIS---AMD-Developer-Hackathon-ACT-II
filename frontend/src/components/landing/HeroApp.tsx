import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Icon, type IconName } from "../ui/icons";
import { EASE } from "../ui/motion";
import { cx, Mark } from "../ui/primitives";

/* A static, illustrative IGNIS window in the style of the linear.app hero.
   Designed at 1320×720 and scaled to fit; all content is synthetic. */

const W = 1320;
const H = 720;

function useFitScale() {
  const ref = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setScale(Math.min(1, entry.contentRect.width / W)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return { ref, scale };
}

export function HeroApp() {
  const { ref, scale } = useFitScale();
  return (
    <div ref={ref} className="relative w-full" style={{ height: H * scale }}>
      <div
        className="absolute top-0 left-1/2 origin-top rounded-[12px] bg-[#0d0d0e] p-2 shadow-[0_0_0_1px_rgb(255_255_255/0.04),0_40px_120px_-30px_rgb(0_0_0/0.9)]"
        style={{ width: W, height: H, transform: `translateX(-50%) scale(${scale})` }}
        aria-label="Illustrative IGNIS workspace with synthetic data"
        role="img"
      >
        <div className="flex size-full overflow-hidden rounded-[10px] border border-line bg-[#111113] text-left tracking-normal">
          <Sidebar />
          <Main />
        </div>
      </div>
    </div>
  );
}

/* Sidebar ------------------------------------------------------------------- */

function NavRow({ icon, label, count, active }: { icon: ReactNode; label: string; count?: number; active?: boolean }) {
  return (
    <div
      className={cx(
        "flex h-[30px] items-center gap-2.5 rounded-[6px] px-2.5 text-[13px] font-[510]",
        active ? "bg-white/[0.06] text-fg" : "text-[#c9c9ce]",
      )}
    >
      <span className="grid size-4 place-items-center text-fg-3">{icon}</span>
      <span className="flex-1">{label}</span>
      {count !== undefined && <span className="text-[12px] font-normal text-fg-4">{count}</span>}
    </div>
  );
}

function Sidebar() {
  const i = (n: IconName) => <Icon name={n} size={14} />;
  return (
    <aside className="flex w-[244px] shrink-0 flex-col gap-0.5 border-r border-line bg-[#0e0e10] p-3">
      <div className="mb-3 flex items-center justify-between px-1.5 pt-1">
        <div className="flex items-center gap-2 text-[13px] font-[590] text-fg">
          <Mark size={18} tile />
          IGNIS
          <span className="text-fg-4">⌄</span>
        </div>
        <div className="flex items-center gap-1 text-fg-3">
          <span className="grid size-7 place-items-center">{i("filter")}</span>
          <span className="grid size-7 place-items-center rounded-full border border-line-strong">{i("doc")}</span>
        </div>
      </div>
      <NavRow icon={i("alert")} label="Alerts" count={1} />
      <NavRow icon={i("doc")} label="Inbox" count={3} />
      <NavRow icon={i("review")} label="Review queue" count={5} />
      <NavRow icon={i("report")} label="Reports" />

      <p className="mt-5 mb-1 px-2.5 text-[12px] font-[510] text-fg-4">Workspace ▾</p>
      <NavRow icon={i("calc")} label="Assets" />
      <NavRow icon={i("spans")} label="Evidence library" />
      <NavRow icon={i("filter")} label="Rules · triage_v1" />

      <p className="mt-5 mb-1 px-2.5 text-[12px] font-[510] text-fg-4">Favorites ▾</p>
      <NavRow icon={<Mark size={13} />} label="P-101 · seal leakage" active />
      <NavRow icon={i("calc")} label="P-102 · coupling" />
      <NavRow icon={i("report")} label="Model benchmarks" />

      <div className="mt-auto rounded-[8px] border border-dashed border-line-strong px-3 py-2.5 text-[11px] leading-snug text-fg-4">
        Illustrative screen · synthetic data
      </div>
    </aside>
  );
}

/* Main issue-style view ------------------------------------------------------ */

const ACTIVITY = [
  { who: "IGNIS", text: "extracted 3 spans from WO-0418 · schema valid", when: "6 min ago" },
  { who: "Long", text: "approved WO-0418 · rev 2", when: "4 min ago" },
  { who: "triage_v1", text: "raised ALT-01 · initial notice on seal · P-101", when: "3 min ago" },
];

function Main() {
  const reduce = useReducedMotion();
  return (
    <div className="relative flex min-w-0 flex-1 flex-col">
      {/* top bar */}
      <div className="flex h-[52px] items-center justify-between border-b border-line px-5">
        <div className="flex items-center gap-2.5 text-[13px] font-[510] text-fg">
          <span className="grid size-4 place-items-center rounded-full border-[1.5px] border-accent">
            <span className="size-1.5 rounded-full bg-accent" />
          </span>
          <span className="text-fg-3">ALT-01</span>
          Seal leakage on P-101
          <span className="text-fg-4">···</span>
        </div>
        <div className="flex items-center gap-4 text-[12px] text-fg-3">
          <span>1 / 6</span>
          <span>↑</span>
          <span>↓</span>
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* document */}
        <div className="min-w-0 flex-1 px-[72px] pt-10">
          <h3 className="text-[20px] leading-[26.6px] font-[590] tracking-[-0.012em] text-[#d6d6da]">Seal leakage on P-101</h3>
          <p className="mt-2 max-w-[560px] text-[14px] leading-[21px] tracking-[-0.013em] text-fg-3">
            Recurring leakage at the drive-end{" "}
            <code className="rounded-[4px] border border-line-strong bg-white/[0.04] px-1 py-px font-mono text-[12px] text-fg-2">
              mechanical seal
            </code>{" "}
            . Priority and band come from{" "}
            <code className="rounded-[4px] border border-line-strong bg-white/[0.04] px-1 py-px font-mono text-[12px] text-fg-2">
              triage_v1
            </code>{" "}
            over approved records only.
          </p>

          <div className="mt-6 flex gap-2">
            {[
              ["Band", "High"],
              ["Priority", "6"],
              ["Approved", "2"],
              ["Pending", "1"],
            ].map(([k, v]) => (
              <div key={k} className="rounded-[6px] border border-line px-2.5 py-1.5">
                <div className="text-[11px] text-fg-4">{k}</div>
                <div className={cx("text-[13px] font-[510]", k === "Band" ? "text-brand-text" : "text-fg")}>{v}</div>
              </div>
            ))}
          </div>

          <p className="mt-9 text-[15px] font-[590] text-[#d6d6da]">Activity</p>
          <ul className="mt-4 space-y-3.5">
            {ACTIVITY.map((a, idx) => (
              <motion.li
                key={a.text}
                initial={reduce ? false : { opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 1.2 + idx * 0.25, duration: 0.6, ease: EASE }}
                className="flex items-center gap-2.5 text-[12.5px] text-fg-4"
              >
                <span className="grid size-[18px] place-items-center rounded-full bg-white/[0.06]">
                  {a.who === "IGNIS" ? <Mark size={11} /> : <span className="size-1.5 rounded-full bg-fg-4" />}
                </span>
                <span>
                  <span className="text-fg-3">{a.who}</span> {a.text} · {a.when}
                </span>
              </motion.li>
            ))}
          </ul>

          <motion.div
            initial={reduce ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 2, duration: 0.7, ease: EASE }}
            className="mt-6 max-w-[600px] rounded-[10px] border border-line bg-white/[0.02] p-4"
          >
            <div className="flex items-center gap-2 text-[13px]">
              <span className="grid size-5 place-items-center rounded-full bg-[#2a2a2e] text-[10px] font-[590] text-fg-2">KT</span>
              <span className="font-[510] text-fg">Tuong</span>
              <span className="text-fg-4">· 2 min ago</span>
            </div>
            <p className="mt-2 text-[13.5px] leading-[21px] text-fg-2">
              Two leaks on the same seal this quarter. Before we order parts, can we check the flush line against the manual?
            </p>
          </motion.div>
        </div>

        {/* properties column */}
        <div className="w-[260px] shrink-0 px-5 pt-8 text-[12.5px]">
          {[
            ["Status", "Investigating"],
            ["Asset", "P-101 (synthetic)"],
            ["Snapshot", "snap_02"],
            ["Evidence pack", "ep_01"],
            ["Owner", "Maintenance expert"],
          ].map(([k, v]) => (
            <div key={k} className="flex items-center justify-between py-1.5">
              <span className="text-fg-4">{k}</span>
              <span className="font-mono text-[11.5px] text-fg-2">{v}</span>
            </div>
          ))}
        </div>
      </div>

      <AssistantPanel />
    </div>
  );
}

/* Floating assistant panel ---------------------------------------------------- */

const DRAFT =
  "Leakage is consistent with seal-face wear [P-01]. A reviewed case links similar leakage to dry running [P-02]. No operating data confirms either cause.";

function useTyped(text: string, start: boolean) {
  const reduce = useReducedMotion();
  const [n, setN] = useState(reduce ? text.length : 0);
  useEffect(() => {
    if (!start || reduce) return;
    let i = 0;
    const id = window.setInterval(() => {
      i += 2;
      setN(Math.min(i, text.length));
      if (i >= text.length) window.clearInterval(id);
    }, 24);
    return () => window.clearInterval(id);
  }, [start, text, reduce]);
  return text.slice(0, n);
}

function AssistantPanel() {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    const t1 = window.setTimeout(() => setPhase(1), 1700);
    const t2 = window.setTimeout(() => setPhase(2), 2700);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
    };
  }, []);
  const typed = useTyped(DRAFT, phase >= 2);
  const done = typed.length === DRAFT.length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 24, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ delay: 1.1, duration: 0.9, ease: EASE }}
      className="absolute right-5 bottom-0 w-[420px] rounded-t-[12px] border border-b-0 border-line-strong bg-[#161618] shadow-[0_-20px_60px_-20px_rgb(0_0_0/0.8)]"
    >
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <div className="flex items-center gap-2 text-[13px] font-[590] text-fg">
          <Mark size={14} />
          IGNIS assistant
          <span className="rounded-[4px] border border-line-strong px-1.5 py-px text-[11px] font-normal text-fg-3">draft only</span>
        </div>
        <div className="flex gap-3 text-fg-4">
          <span>–</span>
          <span>×</span>
        </div>
      </div>
      <div className="space-y-3 p-4">
        <div className="ml-auto w-fit max-w-[340px] rounded-[10px] bg-white/[0.06] px-3 py-2 text-[13px] leading-5 text-fg">
          Explain ALT-01 using only the pinned evidence pack
        </div>
        <AnimatePresence>
          {phase >= 1 && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-end gap-1.5 text-[11.5px] text-fg-4"
            >
              <span className="font-mono text-fg-3">F-01 · P-01 · P-02</span> added to context
            </motion.div>
          )}
        </AnimatePresence>
        {phase >= 2 && (
          <div className="text-[13px] leading-5 text-fg-2">
            <p className="mb-1.5 text-[11.5px] text-fg-4">{done ? "Draft ready · needs expert review ▸" : "Drafting…"}</p>
            <p className="min-h-[60px]">
              {typed}
              {!done && <span className="ml-px inline-block h-3.5 w-px translate-y-0.5 animate-pulse bg-fg" />}
            </p>
          </div>
        )}
        <AnimatePresence>
          {done && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: EASE }}
              className="flex items-center justify-between rounded-[8px] border border-line bg-white/[0.02] px-3 py-2 text-[12px]"
            >
              <span className="text-fg-3">
                Checks <span className="text-ok">4 / 4 passed</span> · citations resolve
              </span>
              <span className="flex gap-1.5">
                <span className="rounded-[6px] bg-accent px-2 py-0.5 font-[510] text-on-brand">Accept</span>
                <span className="rounded-[6px] border border-line-strong px-2 py-0.5 text-fg-2">Reject</span>
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
