import type { ReactNode } from "react";
import { motion } from "motion/react";
import { problem } from "../../content/site";
import { EASE, Reveal } from "../ui/motion";
import { Container, cx } from "../ui/primitives";

/* 02 — Problem: a two-tone statement over three sourced charts (layout of
   Linear's FIG 0.x row). Figures come from issue #21 and were checked against
   the cited reports; they describe the problem, not results measured with IGNIS. */

const grow = {
  hidden: { clipPath: "inset(0 100% 0 0)" },
  show: (i: number) => ({ clipPath: "inset(0 0% 0 0)", transition: { duration: 1.1, ease: EASE, delay: 0.15 + i * 0.12 } }),
};
const rise = {
  hidden: { clipPath: "inset(100% 0 0 0)" },
  show: (i: number) => ({ clipPath: "inset(0% 0 0 0)", transition: { duration: 1.1, ease: EASE, delay: 0.15 + i * 0.15 } }),
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

/** FIG 2.1 — maintenance tracking tools, multiple answers allowed. */
function ToolsChart() {
  const rows = problem.tools.rows;
  return (
    <ChartFrame label={rows.map((r) => `${r.label} ${r.value}%`).join(", ")}>
      <ul className="space-y-5">
        {rows.map((r, i) => (
          <li key={r.label}>
            <div className="mb-2 flex items-baseline justify-between text-[13px]">
              <span className="text-fg-2">{r.label}</span>
              <span className="font-mono text-fg tabular-nums">{r.value}%</span>
            </div>
            <div className="h-2 rounded-full bg-white/[0.06]">
              <motion.div
                custom={i}
                variants={grow}
                className={cx("h-full rounded-full", r.manual ? "bg-accent" : "bg-fg-3")}
                style={{ width: `${r.value}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-4 font-mono text-[11px] text-fg-4">{problem.tools.note}</p>
    </ChartFrame>
  );
}

/** FIG 2.2 — HVAC work orders closed on Friday vs every other day. */
function ClosingChart() {
  const bars = problem.closing.bars;
  const max = Math.max(...bars.map((b) => b.value));
  return (
    <ChartFrame label={bars.map((b) => `${b.label} ${b.value.toLocaleString("en-US")}`).join(", ")}>
      <div className="flex h-[176px] items-end gap-6 border-b border-line-strong px-2">
        {bars.map((b, i) => (
          <div key={b.label} className="flex h-full flex-1 flex-col justify-end">
            <span className="mb-2 font-mono text-[13px] text-fg tabular-nums">{b.value.toLocaleString("en-US")}</span>
            <motion.div
              custom={i}
              variants={rise}
              className={cx("w-full rounded-t-[4px]", i === 0 ? "bg-accent" : "bg-fg-3")}
              style={{ height: `${Math.max(2, (b.value / max) * 130)}px` }}
            />
          </div>
        ))}
      </div>
      <div className="mt-2 flex gap-6 px-2 text-[12px] text-fg-3">
        {bars.map((b) => (
          <span key={b.label} className="flex-1">
            {b.label}
          </span>
        ))}
      </div>
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

const CHARTS = [ToolsChart, ClosingChart, DowntimeChart];

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
