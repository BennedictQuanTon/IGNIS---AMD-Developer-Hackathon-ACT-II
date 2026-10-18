import { useEffect, useRef, useState } from "react";
import { animate, motion, useMotionValue, useMotionValueEvent, useReducedMotion, useTransform } from "motion/react";
import { challenge, demoVideo, features, product, track, type Owner } from "../../content/site";
import { Icon } from "../ui/icons";
import { CountUp, EASE, Reveal, Stagger, StaggerItem, trackSpotlight } from "../ui/motion";
import { cx, Section } from "../ui/primitives";

/* 01 — Challenge and track ------------------------------------------------- */

export function Challenge() {
  return (
    <Section id="challenge" eyebrow="01 — Challenge" title={challenge.title} intro={challenge.intro}>
      <Stagger className="grid grid-cols-2 overflow-hidden rounded-[var(--radius-lg)] border border-line lg:grid-cols-4">
        {challenge.stats.map((s, i) => (
          <StaggerItem
            key={s.label}
            className={cx(
              "border-line p-6 sm:p-8",
              i % 2 === 0 && "border-r",
              i < 2 && "border-b lg:border-b-0",
              i === 1 && "lg:border-r",
              i === 2 && "lg:border-r",
            )}
          >
            <div className="text-[28px] leading-none font-[510] tracking-[-0.03em] text-fg sm:text-[40px] lg:text-[48px]">
              {"prefix" in s && s.prefix}
              <CountUp value={s.value} />
              {"suffix" in s && <span className="text-fg-3">{s.suffix}</span>}
            </div>
            <div className="mt-3 text-[13px] text-fg-3">{s.label}</div>
          </StaggerItem>
        ))}
      </Stagger>

      <div className="mt-16 grid gap-12 lg:mt-20 lg:grid-cols-[1fr_1.1fr] lg:gap-16">
        <Reveal>
          <p className="t-label">{track.title}</p>
          <blockquote className="mt-5 border-l-2 border-accent pl-5">
            <p className="text-[22px] leading-snug font-[510] tracking-[-0.015em] text-fg sm:text-[26px]">
              “{track.quote}”
            </p>
            <p className="mt-4 text-[15px] text-fg-3">“{track.problem}”</p>
          </blockquote>
        </Reveal>

        <Reveal delay={0.1}>
          <figure aria-labelledby="coverage-title">
            <figcaption id="coverage-title" className="mb-4 text-[13px] font-[510] text-fg">
              Factory data sources named in the brief
            </figcaption>
            <CoverageChart />
          </figure>
        </Reveal>
      </div>
    </Section>
  );
}

function CoverageChart() {
  return (
    <motion.ul
      className="space-y-2.5"
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-60px" }}
      transition={{ staggerChildren: 0.09, delayChildren: 0.15 }}
    >
      {track.coverage.map((row) => (
        <li key={row.source} className="grid grid-cols-[132px_1fr] items-center gap-3 sm:grid-cols-[160px_1fr]">
          <span className={cx("text-[13px]", row.status === "out" ? "text-fg-4" : "text-fg-2")}>{row.source}</span>
          <div className="relative h-8 overflow-hidden rounded-[6px] border border-line">
            <motion.div
              aria-hidden
              className={cx(
                "absolute inset-y-0 left-0 origin-left",
                row.status === "now" && "bg-accent",
                row.status === "roadmap" &&
                  "bg-[repeating-linear-gradient(135deg,rgb(255_255_255/0.06)_0_6px,transparent_6px_12px)]",
              )}
              style={{ width: row.status === "out" ? "0%" : "100%" }}
              variants={{ hidden: { scaleX: 0 }, show: { scaleX: 1, transition: { duration: 1.1, ease: EASE } } }}
            />
            <span
              className={cx(
                "relative flex h-full items-center px-3 text-[12px] font-medium",
                row.status === "now" ? "text-on-brand" : row.status === "roadmap" ? "text-fg-2" : "text-fg-4",
              )}
            >
              {row.note}
            </span>
          </div>
        </li>
      ))}
    </motion.ul>
  );
}

/* 03 — Product -------------------------------------------------------------- */

const ownerStyle: Record<Owner, string> = {
  AI: "text-fg-3 border-line-strong",
  CODE: "text-fg-3 border-line-strong",
  HUMAN: "text-brand-text border-accent/40",
};

/** A packet of evidence travels the flow; each node lights up as it passes. */
function useFlowProgress(count: number) {
  const reduce = useReducedMotion();
  const progress = useMotionValue(0);
  const [active, setActive] = useState(-1);

  useEffect(() => {
    if (reduce) return;
    const controls = animate(progress, [0, 1], { duration: 9, ease: "linear", repeat: Infinity, repeatDelay: 0.6 });
    return () => controls.stop();
  }, [progress, reduce]);

  useMotionValueEvent(progress, "change", (v) => setActive(Math.min(count - 1, Math.floor(v * count))));
  return { progress, active, reduce };
}

function FlowDiagram() {
  const steps = product.flow;
  const { progress, active, reduce } = useFlowProgress(steps.length);
  const left = useTransform(progress, (v) => `${v * 100}%`);
  const top = useTransform(progress, (v) => `${v * 100}%`);

  return (
    <div className="relative">
      {/* horizontal rail (desktop) */}
      <div aria-hidden className="absolute top-1/2 right-[7%] left-[7%] hidden h-px bg-line-strong lg:block">
        {!reduce && (
          <motion.span style={{ left }} className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2">
            <span className="block h-px w-24 -translate-x-1/2 bg-gradient-to-r from-transparent via-accent to-transparent" />
            <span className="absolute top-1/2 left-0 size-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent shadow-[0_0_14px_4px_rgb(255_196_0/0.6)]" />
          </motion.span>
        )}
      </div>
      {/* vertical rail (mobile) */}
      <div aria-hidden className="absolute top-[6%] bottom-[6%] left-[19px] w-px bg-line-strong lg:hidden">
        {!reduce && (
          <motion.span
            style={{ top }}
            className="absolute left-1/2 size-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent shadow-[0_0_14px_4px_rgb(255_196_0/0.6)]"
          />
        )}
      </div>

      <Stagger className="relative grid gap-3 lg:grid-cols-7 lg:gap-3">
        {steps.map((s, i) => {
          const lit = reduce || i === active;
          return (
            <StaggerItem key={s.label} className="flex items-center gap-4 lg:block">
              <span
                aria-hidden
                className={cx(
                  "relative z-10 grid size-10 shrink-0 place-items-center rounded-full border bg-bg font-mono text-[11px] transition-colors duration-500 lg:hidden",
                  lit ? "border-accent text-brand-text" : "border-line-strong text-fg-3",
                )}
              >
                {i + 1}
              </span>
              <div
                className={cx(
                  "relative z-10 flex-1 rounded-[var(--radius)] border bg-elevated px-3 py-3.5 transition-[border-color,box-shadow,background-color] duration-500 lg:min-h-[104px]",
                  lit && !reduce
                    ? "border-accent/60 bg-card shadow-[0_0_0_4px_rgb(255_196_0/0.08),0_12px_32px_-12px_rgb(255_196_0/0.5)]"
                    : "border-line",
                )}
              >
                <span
                  className={cx(
                    "inline-block rounded-[4px] border px-1.5 py-px font-mono text-[10px] font-medium tracking-wider",
                    ownerStyle[s.owner],
                  )}
                >
                  {s.owner}
                </span>
                <div className="mt-2.5 text-[13px] leading-snug font-medium text-fg">{s.label}</div>
              </div>
            </StaggerItem>
          );
        })}
      </Stagger>
    </div>
  );
}

export function Product() {
  return (
    <Section id="product" eyebrow="03 — Product" title={product.title} intro={product.intro}>
      <Reveal>
        <DemoVideo />
      </Reveal>
    </Section>
  );
}

/** Demo film: fetched when near the viewport, autoplays muted while at least half visible
    (browsers block autoplay with sound), pauses when scrolled away; sound toggle top right. */
function DemoVideo() {
  const frame = useRef<HTMLDivElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const reduce = useReducedMotion();
  const [near, setNear] = useState(false);
  const [inView, setInView] = useState(false);
  const [muted, setMuted] = useState(true);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const el = frame.current;
    if (!el) return;
    const preload = new IntersectionObserver(([entry]) => entry.isIntersecting && setNear(true), { rootMargin: "600px 0px" });
    const visible = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), { threshold: 0.5 });
    preload.observe(el);
    visible.observe(el);
    return () => {
      preload.disconnect();
      visible.disconnect();
    };
  }, []);

  // Play once the source is attached and at least half the frame is visible; pause when it leaves.
  useEffect(() => {
    const v = video.current;
    if (!v || !near) return;
    if (inView && !reduce) void v.play().catch(() => undefined);
    else if (!inView) v.pause();
  }, [near, inView, reduce]);

  const toggleSound = () => {
    const v = video.current;
    if (!v) return;
    v.muted = !v.muted;
    setMuted(v.muted);
    if (v.paused) void v.play().catch(() => undefined);
  };
  const togglePlay = () => {
    const v = video.current;
    if (!v) return;
    if (v.paused) void v.play().catch(() => undefined);
    else v.pause();
  };

  return (
    <div ref={frame} className="rounded-[12px] bg-[#0d0d0e] p-2 shadow-[0_0_0_1px_rgb(255_255_255/0.04),0_40px_120px_-30px_rgb(0_0_0/0.9)]">
      <div className="group relative aspect-video overflow-hidden rounded-[10px] border border-line bg-black">
        <video
          ref={video}
          className="absolute inset-0 size-full cursor-pointer object-cover"
          src={near ? demoVideo.src : undefined}
          poster={demoVideo.poster}
          preload={near ? "auto" : "none"}
          muted={muted}
          loop
          playsInline
          onClick={togglePlay}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onTimeUpdate={(e) => {
            const v = e.currentTarget;
            if (v.duration) setProgress(v.currentTime / v.duration);
          }}
          aria-label={demoVideo.label}
        />

        <button
          type="button"
          onClick={toggleSound}
          aria-label={muted ? "Turn sound on" : "Turn sound off"}
          aria-pressed={!muted}
          className="absolute top-4 right-4 grid size-10 place-items-center rounded-full border border-white/15 bg-black/55 text-white backdrop-blur-md transition-colors hover:bg-black/75"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <path d="M11 5 6 9H3v6h3l5 4V5Z" />
            {muted ? <path d="m16 9 5 6m0-6-5 6" /> : <path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13" />}
          </svg>
        </button>

        {!playing && (
          <button
            type="button"
            onClick={togglePlay}
            aria-label="Play the IGNIS demo film"
            className="absolute inset-0 grid place-items-center bg-black/25 transition-colors hover:bg-black/10"
          >
            <span className="grid size-20 place-items-center rounded-full bg-accent text-on-brand shadow-[0_12px_40px_-8px_rgb(255_196_0/0.6)]">
              <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden className="translate-x-0.5 fill-current">
                <path d="M7 4.5v15l12-7.5-12-7.5Z" />
              </svg>
            </span>
          </button>
        )}

        <div aria-hidden className="absolute inset-x-0 bottom-0 h-[3px] bg-white/10">
          <div className="h-full bg-accent" style={{ width: `${progress * 100}%` }} />
        </div>
      </div>
    </div>
  );
}

/* Features ------------------------------------------------------------------ */

export function Features() {
  return (
    <Section eyebrow="Core features" title="Six building blocks, one workflow">
      <Reveal>
        <FlowDiagram />
      </Reveal>
      <Reveal className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-[12px] text-fg-3" delay={0.1}>
        <span className="flex items-center gap-2">
          <span className="rounded-[4px] border border-line-strong px-1.5 font-mono text-[10px]">AI</span> proposes
        </span>
        <span className="flex items-center gap-2">
          <span className="rounded-[4px] border border-line-strong px-1.5 font-mono text-[10px]">CODE</span> computes
        </span>
        <span className="flex items-center gap-2">
          <span className="rounded-[4px] border border-accent/40 px-1.5 font-mono text-[10px] text-brand-text">HUMAN</span>{" "}
          approves
        </span>
      </Reveal>
      <Reveal className="mt-10 mb-14 max-w-2xl" delay={0.15}>
        <p className="text-[14px] leading-relaxed text-fg-3">
          {product.analogy}{" "}
          <a
            href={product.analogyHref}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-fg-2 underline decoration-line-strong underline-offset-4 transition-colors hover:text-fg hover:decoration-fg-3"
          >
            Architecture explained <Icon name="external" size={12} />
          </a>
        </p>
      </Reveal>
      <Stagger className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((f) => (
          <StaggerItem key={f.title}>
            <article
              onPointerMove={trackSpotlight}
              className="spotlight group relative h-full overflow-hidden rounded-[var(--radius-lg)] border border-line bg-elevated p-6 transition-colors duration-300 hover:bg-card"
            >
              <div className="relative grid size-9 place-items-center rounded-[var(--radius)] border border-line-strong bg-bg text-fg-2 transition-colors duration-300 group-hover:border-accent/50 group-hover:text-brand-text">
                <Icon name={f.icon} />
              </div>
              <h3 className="relative mt-5 text-[15px] font-[510] text-fg">{f.title}</h3>
              <p className="relative mt-2 text-[14px] leading-relaxed text-fg-2">{f.body}</p>
            </article>
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}
