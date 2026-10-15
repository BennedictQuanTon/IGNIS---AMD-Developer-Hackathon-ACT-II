import { useRef } from "react";
import { motion, useReducedMotion, useScroll, useTransform } from "motion/react";
import {
  benchmarkMetrics,
  comparison,
  delivered,
  maintieSplit,
  productScreenshot,
  REPO,
  sources,
  team,
  type Cell,
} from "../../content/site";
import { Icon } from "../ui/icons";
import { CountUp, EASE, Reveal, Stagger, StaggerItem, trackSpotlight } from "../ui/motion";
import { ButtonLink, Container, cx, Section, Wordmark } from "../ui/primitives";
import { Workspace } from "../../workspace/Workspace";

/* 04 — Inside IGNIS: the real workspace preview, embedded and interactive ---- */

export function ProductFrame() {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "start 30%"] });
  const rotateX = useTransform(scrollYProgress, [0, 1], [reduce ? 0 : 18, 0]);
  const scale = useTransform(scrollYProgress, [0, 1], [reduce ? 1 : 0.94, 1]);
  const opacity = useTransform(scrollYProgress, [0, 0.5], [reduce ? 1 : 0.4, 1]);

  return (
    <Section
      eyebrow="03 — Inside IGNIS"
      title="The review workspace"
      intro="Six stages from source file to signed report. Try it below."
    >
      <div ref={ref} style={{ perspective: 1600 }}>
        <motion.div
          style={{ rotateX, scale, opacity, transformOrigin: "50% 0%" }}
          className="rounded-[12px] bg-[#0d0d0e] p-2 shadow-[0_0_0_1px_rgb(255_255_255/0.04),0_60px_140px_-40px_rgb(0_0_0/1)]"
        >
          <div className="relative overflow-hidden rounded-[10px] border border-line">
            {productScreenshot ? (
              <img src={productScreenshot.src} alt="IGNIS review workspace" className="block w-full" />
            ) : (
              <>
                <div className="hidden h-[760px] md:block">
                  <Workspace embedded />
                </div>
                <a
                  href="#/app"
                  className="flex items-center justify-between gap-4 bg-elevated p-5 text-[14px] text-fg-2 md:hidden"
                >
                  Open the workspace preview <Icon name="arrow" size={14} />
                </a>
              </>
            )}
          </div>
        </motion.div>
      </div>
      {productScreenshot && <p className="mt-4 font-mono text-[12px] text-fg-4">{productScreenshot.caption}</p>}
    </Section>
  );
}

/* 05 — Delivered ------------------------------------------------------------- */

function ChainVisual() {
  return (
    <div className="flex gap-1" aria-hidden>
      {Array.from({ length: 9 }, (_, i) => (
        <motion.span
          key={i}
          className="h-2 flex-1 rounded-[2px] bg-accent"
          initial={{ opacity: 0.12 }}
          whileInView={{ opacity: [0.12, 1, 0.75] }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 + i * 0.09, ease: EASE }}
        />
      ))}
    </div>
  );
}

function SplitVisual() {
  const total = maintieSplit.reduce((s, d) => s + d.count, 0);
  const colors = ["bg-fg-2", "bg-fg-4", "bg-accent"];
  return (
    <figure>
      <div
        className="flex h-3 gap-0.5 overflow-hidden rounded-full"
        role="img"
        aria-label={maintieSplit.map((d) => `${d.name} ${d.count}`).join(", ")}
      >
        {maintieSplit.map((d, i) => (
          <motion.span
            key={d.name}
            className={cx("h-full origin-left", colors[i])}
            style={{ width: `${(d.count / total) * 100}%` }}
            initial={{ clipPath: "inset(0 100% 0 0)" }}
            whileInView={{ clipPath: "inset(0 0% 0 0)" }}
            viewport={{ once: true }}
            transition={{ duration: 0.9, ease: EASE, delay: 0.3 + i * 0.25 }}
          />
        ))}
      </div>
      <figcaption className="mt-2 flex justify-between font-mono text-[10px] text-fg-3">
        {maintieSplit.map((d) => (
          <span key={d.name}>
            {d.name} {d.count}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}

export function Delivered() {
  return (
    <Section eyebrow="04 — Delivered" title="Built and verifiable today">
      <Stagger className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {delivered.map((m) => (
          <StaggerItem key={m.label}>
            <article
              onPointerMove={trackSpotlight}
              className="spotlight relative flex h-full flex-col rounded-[var(--radius-lg)] border border-line bg-elevated p-6"
            >
              <div className="relative text-[44px] leading-none font-[510] tracking-[-0.035em] text-fg">
                <CountUp value={m.value} />
                {"secondary" in m && (
                  <>
                    <span className="mx-1.5 text-fg-4">·</span>
                    <CountUp value={m.secondary} />
                  </>
                )}
              </div>
              <p className="relative mt-3 text-[13px] leading-relaxed text-fg-2">{m.label}</p>
              <div className="relative mt-auto pt-6">
                {m.visual === "chain" && <ChainVisual />}
                {m.visual === "split" && <SplitVisual />}
                <p className={cx("font-mono text-[10px] text-fg-4", m.visual !== "none" && "mt-3")}>{m.source}</p>
              </div>
            </article>
          </StaggerItem>
        ))}
      </Stagger>

      <Reveal className="mt-4 text-[12px] text-fg-3">
        Test answers stay out of prompts and retrieval until the configuration is frozen.
      </Reveal>

      <Reveal delay={0.1} className="mt-8">
        <div className="rounded-[var(--radius-lg)] border border-dashed border-line-strong p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-[15px] font-[510] text-fg">Model benchmarks on AMD Token Factory</h3>
            <span className="rounded-full bg-warn/12 px-2 py-0.5 text-[11px] font-medium text-warn">
              Pending measurement
            </span>
          </div>
          <ul className="mt-5 grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-4">
            {benchmarkMetrics.map((name) => (
              <li key={name}>
                <div className="text-[13px] text-fg-2">{name}</div>
                <div className="mt-2 h-1.5 rounded-full bg-white/[0.05]" />
                <div className="mt-1.5 font-mono text-[10px] text-fg-4">not yet measured</div>
              </li>
            ))}
          </ul>
          <p className="mt-5 text-[12px] text-fg-3">
            Filled only from measured runs in{" "}
            <a href={`${REPO}/issues/18`} target="_blank" rel="noreferrer" className="text-fg-2 underline underline-offset-4">
              issue #18
            </a>
            , with model ID, sample size and test date.
          </p>
        </div>
      </Reveal>
    </Section>
  );
}

/* 06 — Comparison ----------------------------------------------------------- */

function CellMark({ value }: { value: Cell }) {
  switch (value) {
    case "yes":
      return (
        <span className="inline-flex text-ok" aria-label="Yes">
          <Icon name="check" />
        </span>
      );
    case "no":
      return (
        <span className="inline-flex text-fg-4" aria-label="No">
          <Icon name="dash" />
        </span>
      );
    case "partial":
      return <span className="text-[12px] text-fg-3">Partial</span>;
    case "na":
      return <span className="text-[12px] text-fg-4">n/a</span>;
    case "progress":
      return (
        <span className="inline-flex items-center gap-1.5 text-[12px] text-ok">
          <Icon name="check" size={14} />
          <span className="text-fg-3">in progress</span>
        </span>
      );
  }
}

export function Comparison() {
  const last = comparison.columns.length - 1;
  return (
    <Section
      id="comparison"
      eyebrow="05 — Why IGNIS"
      title="Traceable by design"
      intro="Compared by design properties, not by benchmark scores."
    >
      <Reveal>
        <div className="scrollbar-thin overflow-x-auto rounded-[var(--radius-lg)] border border-line">
          <table className="w-full min-w-[720px] border-collapse text-left text-[13px]">
            <thead>
              <tr className="border-b border-line">
                <th scope="col" className="px-5 py-4 font-medium text-fg-3">
                  Capability
                </th>
                {comparison.columns.map((c, i) => (
                  <th
                    key={c}
                    scope="col"
                    className={cx(
                      "relative px-4 py-4 text-center font-medium",
                      i === last ? "bg-accent-soft text-fg" : "text-fg-3",
                    )}
                  >
                    {i === last && (
                      <motion.span
                        aria-hidden
                        className="absolute inset-x-0 top-0 h-0.5 origin-left bg-accent"
                        initial={{ clipPath: "inset(0 100% 0 0)" }}
                        whileInView={{ clipPath: "inset(0 0% 0 0)" }}
                        viewport={{ once: true }}
                        transition={{ duration: 1, ease: EASE, delay: 0.3 }}
                      />
                    )}
                    {i === last ? <Wordmark height={14} className="mx-auto" /> : c}
                  </th>
                ))}
              </tr>
            </thead>
            <motion.tbody
              initial="hidden"
              whileInView="show"
              viewport={{ once: true, margin: "-60px" }}
              variants={{ show: { transition: { staggerChildren: 0.06 } } }}
            >
              {comparison.rows.map((row) => (
                <motion.tr
                  key={row.capability}
                  variants={{ hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } } }}
                  className="border-b border-line transition-colors last:border-b-0 hover:bg-white/[0.02]"
                >
                  <th scope="row" className="px-5 py-3.5 font-normal text-fg-2">
                    {row.capability}
                  </th>
                  {row.cells.map((cell, i) => (
                    <td key={i} className={cx("px-4 py-3.5 text-center", i === last && "bg-accent-soft")}>
                      <CellMark value={cell} />
                    </td>
                  ))}
                </motion.tr>
              ))}
            </motion.tbody>
          </table>
        </div>
        <p className="mt-4 text-[12px] text-fg-3">{comparison.footnote}</p>
      </Reveal>
    </Section>
  );
}

/* 07 — Team ------------------------------------------------------------------ */

export function Team() {
  return (
    <Section id="team" eyebrow="06 — Team" title={team.name}>
      <Stagger className="grid gap-3 md:grid-cols-3">
        {team.members.map((m) => (
          <StaggerItem key={m.github}>
            <article
              onPointerMove={trackSpotlight}
              className="spotlight group relative h-full overflow-hidden rounded-[var(--radius-lg)] border border-line bg-elevated"
            >
              <div className="relative aspect-[4/5] overflow-hidden border-b border-line bg-hover">
                <img
                  src={m.photo.src}
                  alt={`Portrait of ${m.name}`}
                  loading="lazy"
                  style={{ transformOrigin: m.photo.origin, objectPosition: m.photo.origin, ["--s" as string]: m.photo.scale }}
                  className="size-full scale-[var(--s)] object-cover transition-[scale] duration-700 ease-[var(--ease-out-expo)] group-hover:scale-[calc(var(--s)*1.04)]"
                />
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0 bg-gradient-to-t from-elevated via-elevated/10 to-transparent"
                />
                <span
                  aria-hidden
                  className="absolute inset-x-0 bottom-0 h-px origin-left scale-x-0 bg-accent transition-transform duration-700 ease-[var(--ease-out-expo)] group-hover:scale-x-100"
                />
              </div>
              <div className="relative p-6 pt-5">
              <h3 className="text-[16px] font-[510] text-fg">{m.name}</h3>
              <p className="relative mt-1 text-[13px] text-brand-text">{m.role}</p>
              <a
                href={`https://github.com/${m.github}`}
                target="_blank"
                rel="noreferrer"
                className="relative mt-3 inline-flex items-center gap-1.5 font-mono text-[12px] text-fg-3 hover:text-fg"
              >
                <Icon name="github" size={12} />@{m.github}
              </a>
              </div>
            </article>
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}

/* 08 — Sources --------------------------------------------------------------- */

export function Sources() {
  return (
    <Section eyebrow="07 — Sources" title="Where every claim comes from">
      <Stagger className="grid gap-x-10 sm:grid-cols-2">
        {sources.map((s) => (
          <StaggerItem key={s.href}>
            <a
              href={s.href}
              target="_blank"
              rel="noreferrer"
              className="group flex items-baseline gap-4 border-b border-line py-3.5 transition-colors hover:border-line-strong"
            >
              <span className="w-24 shrink-0 font-mono text-[11px] text-fg-4">{s.label}</span>
              <span className="flex-1 text-[14px] text-fg-2 transition-colors group-hover:text-fg">{s.text}</span>
              <Icon
                name="external"
                size={12}
                className="shrink-0 text-fg-4 transition-all duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-fg-2"
              />
            </a>
          </StaggerItem>
        ))}
      </Stagger>
      <Reveal className="mt-6 text-[12px] text-fg-3">
        Repository links resolve once the repository is public; that is a separate team decision.
      </Reveal>
    </Section>
  );
}

/* Closing --------------------------------------------------------------------- */

export function Closing() {
  return (
    <section className="py-32 sm:py-44">
      <Container className="text-center">
        <Reveal>
          <h2 className="t-closing mx-auto max-w-[760px] text-fg">
            Traceable by default.
            <br />
            <span className="text-fg-3">Approved by people.</span>
          </h2>
        </Reveal>
        <Reveal delay={0.15} className="mt-10 flex flex-wrap items-center justify-center gap-3">
          <ButtonLink href="#/app">
            Open workspace <Icon name="arrow" size={13} />
          </ButtonLink>
          <ButtonLink href={`${REPO}/issues/16`} external variant="outline">
            Read the proposal
          </ButtonLink>
        </Reveal>
      </Container>
    </section>
  );
}

/* Footer ------------------------------------------------------------------------ */

const footerCols = [
  {
    title: "Product",
    links: [
      { label: "Workspace preview", href: "#/app" },
      { label: "How it works", href: "#product" },
      { label: "Comparison", href: "#comparison" },
    ],
  },
  {
    title: "Project",
    links: [
      { label: "Proposal #16", href: `${REPO}/issues/16` },
      { label: "Backend #17", href: `${REPO}/issues/17` },
      { label: "Models #18", href: `${REPO}/issues/18` },
      { label: "Frontend #19", href: `${REPO}/issues/19` },
    ],
  },
  {
    title: "Data",
    links: [
      { label: "MaintIE", href: "https://github.com/nlp-tlp/maintie" },
      { label: "MaintIE paper", href: "https://aclanthology.org/2024.lrec-main.954.pdf" },
      { label: "AMD API docs", href: "https://amd-aim.github.io/radeon-cloud-docs/api/chat-completions/" },
    ],
  },
  {
    title: "Team",
    links: team.members.map((m) => ({ label: m.name, href: `https://github.com/${m.github}` })),
  },
];

export function Footer() {
  return (
    <footer className="border-t border-line pt-14 pb-16">
      <Container>
        <div className="grid gap-10 md:grid-cols-[1.4fr_repeat(4,1fr)]">
          <div>
            <Wordmark height={18} />
            <p className="mt-4 max-w-[240px] text-[13px] leading-5 text-fg-4">
              Built for AMD Developer Hackathon ACT III · MIT License
            </p>
          </div>
          {footerCols.map((col) => (
            <div key={col.title}>
              <h3 className="text-[13px] leading-5 font-[510] tracking-[-0.01em] text-fg">{col.title}</h3>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((l) => (
                  <li key={l.label}>
                    <a
                      href={l.href}
                      {...(l.href.startsWith("http") ? { target: "_blank", rel: "noreferrer" } : {})}
                      className="text-[13px] leading-5 text-fg-3 transition-colors hover:text-fg"
                    >
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <p className="mt-16 text-[12px] text-fg-4">
          Synthetic demo data is labelled as synthetic. No factory connection, failure prediction or production savings
          are claimed.
        </p>
      </Container>
    </footer>
  );
}
