import type { ReactNode } from "react";
import { Reveal } from "./motion";

export function cx(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(" ");
}

/** 1280px content column; at a 1440px viewport the text edge sits at x=80, as on linear.app. */
export function Container({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("mx-auto w-full max-w-[1344px] px-4 sm:px-8", className)}>{children}</div>;
}

/** Linear section header: label + 48px title on the left, 24px lead on the right. */
export function Section({
  id,
  eyebrow,
  title,
  intro,
  children,
}: {
  id?: string;
  eyebrow: string;
  title: ReactNode;
  intro?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section id={id} className="relative py-24 sm:py-32">
      <Container>
        <Reveal className="grid gap-6 border-t border-line pt-8 md:grid-cols-2 md:gap-12">
          <div>
            <p className="t-label">{eyebrow}</p>
            <h2 className="t-h2 mt-5 max-w-[560px] text-fg">{title}</h2>
          </div>
          {intro && <p className="t-lead max-w-[566px] self-end text-fg-2 md:pt-10">{intro}</p>}
        </Reveal>
        <div className="mt-14 sm:mt-20">{children}</div>
      </Container>
    </section>
  );
}

type ButtonProps = {
  href: string;
  children: ReactNode;
  variant?: "brand" | "light" | "outline" | "ghost";
  external?: boolean;
  className?: string;
};

/** Pill buttons sized like Linear's header CTA: 32px tall, 13px/510, 12px side padding. */
export function ButtonLink({ href, children, variant = "brand", external, className }: ButtonProps) {
  const styles = {
    brand: "bg-accent text-on-brand hover:bg-accent-hover",
    light: "bg-[#e5e5e6] text-on-brand hover:bg-white",
    outline: "border border-line-strong text-fg hover:bg-white/[0.06]",
    ghost: "text-fg-3 hover:text-fg",
  }[variant];
  return (
    <a
      href={href}
      {...(external ? { target: "_blank", rel: "noreferrer" } : {})}
      className={cx(
        "group inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-[13px] font-[510] tracking-normal whitespace-nowrap transition-colors duration-200",
        variant !== "ghost" && "px-3.5",
        styles,
        className,
      )}
    >
      {children}
    </a>
  );
}

const tone = {
  ok: "text-ok bg-ok/12",
  warn: "text-warn bg-warn/12",
  danger: "text-danger bg-danger/12",
  info: "text-info bg-info/12",
  neutral: "text-fg-3 bg-white/6",
  synthetic: "text-synthetic bg-synthetic/12",
  accent: "text-brand-text bg-accent-soft",
  plain: "text-fg-2 bg-white/6",
} as const;

export type Tone = keyof typeof tone;

export function Badge({ children, t = "plain", dot = true, mono }: { children: ReactNode; t?: Tone; dot?: boolean; mono?: boolean }) {
  return (
    <span
      className={cx(
        "inline-flex h-5 shrink-0 items-center gap-1.5 rounded-full px-2 text-[12px] font-medium tracking-[0.01em] whitespace-nowrap",
        mono && "font-mono",
        tone[t],
      )}
    >
      {dot && <span aria-hidden className="size-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

const FLAME =
  "M25 1C27.5 5.5 30 8.5 30 13A6 6 0 0 1 18 13C18 10.5 19.5 8.6 21 7.4C21 9.4 22 10.6 23 10.8C23 7 23.5 3.8 25 1Z";

/** Official reverse wordmark from public/brand (never retyped in a font). */
export function Wordmark({ className, height = 20 }: { className?: string; height?: number }) {
  return (
    <svg
      viewBox="0 0 156 40"
      height={height}
      width={(height * 156) / 40}
      role="img"
      aria-label="IGNIS"
      className={cx("shrink-0", className)}
    >
      <rect x="0" y="0" width="8" height="40" fill="#F5F4F2" />
      <path d="M52 4H20V36H48V22H36" fill="none" stroke="#F5F4F2" strokeWidth="8" />
      <rect x="60" y="0" width="8" height="40" fill="#F5F4F2" />
      <rect x="88" y="0" width="8" height="40" fill="#F5F4F2" />
      <polygon points="60,0 70,0 96,40 86,40" fill="#F5F4F2" />
      <path transform="translate(92 -0.667) scale(0.667)" d={FLAME} fill="#FFC400" />
      <rect x="104" y="14" width="8" height="26" fill="#F5F4F2" />
      <path d="M156 4H124V20H152V36H120" fill="none" stroke="#F5F4F2" strokeWidth="8" />
    </svg>
  );
}

/** Flame-i mark for small sizes (sidebar, avatars). */
export function Mark({ size = 16, className, tile }: { size?: number; className?: string; tile?: boolean }) {
  return (
    <svg viewBox="0 0 48 48" width={size} height={size} aria-hidden className={cx("shrink-0", className)}>
      {tile && <rect width="48" height="48" rx="10" fill="#FFC400" />}
      <path transform="translate(0 3)" d={FLAME} fill={tile ? "#0B0B0C" : "#FFC400"} />
      <rect x="19" y="25" width="10" height="18" fill={tile ? "#0B0B0C" : "#F5F4F2"} />
    </svg>
  );
}
