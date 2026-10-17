import type { ReactNode } from "react";
import { motion } from "motion/react";
import { problem } from "../../content/site";
import { EASE, Reveal } from "../ui/motion";
import { Container, cx } from "../ui/primitives";

/* 02 — Problem: a two-tone statement over three sourced charts (layout of
   Linear's FIG 0.x row). Figures were checked against the cited primary sources
   (MaintainX 2025, Woods et al. 2024, Siemens 2024); they describe the problem,
   not results measured with IGNIS. */

const grow = {
  hidden: { clipPath: "inset(0 100% 0 0)" },
  show: (i: number) => ({ clipPath: "inset(0 0% 0 0)", transition: { duration: 1.1, ease: EASE, delay: 0.15 + i * 0.12 } }),
};

function ChartFrame({ children, label }: { children: ReactNode; label: string }) {
  return (
    <motion.figure
      role="img"
      aria-label={label}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-60px" }}
      className="flex h-[220px] flex-col justify-end"
    >
      {children}
    </motion.figure>
  );
}

/** FIG 2.1 — preventive intent vs. reactive reality (MaintainX 2025). */
function ReactiveChart() {
  const rows = problem.reactive.rows;
  return (
    <ChartFrame label={rows.map((r) => `${r.label} ${r.display}`).join(", ")}>
      <ul className="space-y-5">
        {rows.map((r, i) => (
          <li key={r.label}>
            <div className="mb-2 flex items-baseline justify-between gap-3 text-[13px]">
              <span className="text-fg-2">{r.label}</span>
              <span className="shrink-0 font-mono text-fg tabular-nums">{r.display}</span>
            </div>
            <div className="h-2 rounded-full bg-white/[0.06]">
              <motion.div
                custom={i}
                variants={grow}
                className={cx("h-full rounded-full", r.gap ? "bg-accent" : "bg-fg-3")}
                style={{ width: `${r.value}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-4 font-mono text-[11px] text-fg-4">{problem.reactive.note}</p>
    </ChartFrame>
  );
}

const cell = {
  hidden: { opacity: 0, scale: 0.6 },
  show: (i: number) => ({ opacity: 1, scale: 1, transition: { duration: 0.35, ease: EASE, delay: 0.1 + i * 0.008 } }),
};

/** FIG 2.2 — share of pump work orders with data-quality issues (Woods et al. 2024). */
function QualityChart() {
  const { issues, noVerb, note } = problem.quality;
  return (
    <ChartFrame label={`${issues}% of records with data-quality issues; ${noVerb}% with no activity verb`}>
      <div className="flex items-end gap-5">
        <div className="grid shrink-0 grid-cols-10 gap-[3px]" aria-hidden>
          {Array.from({ length: 100 }, (_, i) => (
            <motion.span
              key={i}
              custom={i}
              variants={cell}
              className={cx("size-[9px] rounded-[2px]", i < issues ? "bg-accent" : "bg-white/[0.08]")}
            />
          ))}
        </div>
        <div className="min-w-0 pb-0.5">
          <div className="font-mono text-[28px] leading-none text-fg tabular-nums">{issues}%</div>
          <div className="mt-1 text-[12px] leading-snug text-fg-3">of records with data-quality issues</div>
          <div className="mt-4 font-mono text-[15px] leading-none text-fg tabular-nums">{noVerb}%</div>
          <div className="mt-1 text-[12px] leading-snug text-fg-3">gave no verb for the work done</div>
        </div>
      </div>
      <p className="mt-4 font-mono text-[11px] text-fg-4">{note}</p>
    </ChartFrame>
  );
}

/** FIG 2.3 — cost of one hour of unplanned downtime by sector. */
function DowntimeChart() {
  const rows = problem.downtime.rows;
  const max = Math.max(...rows.map((r) => r.value));
  return (
    <ChartFrame label={rows.map((r) => `${r.label} ${r.display} per hour`).join(", ")}>
      <ul className="space-y-6">
        {rows.map((r, i) => (
          <li key={r.label}>
            <div className="mb-2 flex items-baseline justify-between text-[13px]">
              <span className="text-fg-2">{r.label}</span>
              <span className="font-mono text-fg tabular-nums">
                {r.display}
                <span className="text-fg-4"> / hour</span>
              </span>
            </div>
            <div className="h-2 rounded-full bg-white/[0.06]">
              <motion.div
                custom={i}
                variants={grow}
                className={cx("h-full min-w-1 rounded-full", i === 0 ? "bg-accent" : "bg-fg-3")}
                style={{ width: `${(r.value / max) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-4 font-mono text-[11px] text-fg-4">{problem.downtime.note}</p>
    </ChartFrame>
  );
}

const CHARTS = [ReactiveChart, QualityChart, DowntimeChart];

export function Problem() {
  return (
    <section id="problem" className="py-24 sm:py-32">
      <Container>
        <Reveal className="border-t border-line pt-8">
          <p className="t-label">02 — Problem</p>
          <h2 className="t-h2 mt-5 max-w-[1250px]">
            <span className="text-fg">{problem.lead}</span> <span className="text-fg-3">{problem.rest}</span>
          </h2>
        </Reveal>

        <div className="mt-20 grid md:grid-cols-3 sm:mt-28">
          {problem.figures.map((f, i) => {
            const Chart = CHARTS[i];
            return (
              <Reveal
                key={f.fig}
                delay={i * 0.1}
                className={cx(
                  "flex flex-col border-line py-10 md:py-0",
                  i > 0 && "border-t md:border-t-0 md:border-l md:pl-8",
                  i < 2 && "md:pr-8",
                )}
              >
                <p className="t-label">{f.fig}</p>
                <div className="my-8 md:my-10">
                  <Chart />
                </div>
                <h3 className="text-[15px] leading-6 font-[510] text-fg">{f.title}</h3>
                <p className="mt-1 max-w-[368px] text-[15px] leading-6 text-fg-3">{f.body}</p>
                <a
                  href={f.source.href}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-4 font-mono text-[11px] leading-5 text-fg-4 underline decoration-line-strong underline-offset-4 transition-colors hover:text-fg-2"
                >
                  {f.source.label}
                </a>
              </Reveal>
            );
          })}
        </div>

        <Reveal className="mt-14">
          <p className="text-[13px] text-fg-4">{problem.disclaimer}</p>
        </Reveal>
      </Container>
    </section>
  );
}
