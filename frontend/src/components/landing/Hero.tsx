import { motion } from "motion/react";
import { hero, REPO } from "../../content/site";
import { Icon } from "../ui/icons";
import { EASE } from "../ui/motion";
import { Container } from "../ui/primitives";
import { HeroApp } from "./HeroApp";

/* Linear hero: left-aligned two-line display, subline with a right-aligned
   announcement, then the product window bleeding off the fold. */
export function Hero() {
  const lines = hero.headline;

  return (
    <section id="top" className="relative overflow-hidden pt-[150px] sm:pt-[200px] lg:pt-[272px]">
      {/* faint top light, no colour */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-40 left-1/2 h-[520px] w-[1200px] -translate-x-1/2 bg-[radial-gradient(closest-side,rgb(255_255_255/0.05),transparent)]"
      />
      <Container className="relative">
        <h1 className="t-display max-w-[900px] text-fg">
          <span className="sr-only">{lines.join(" ")}</span>
          {lines.map((line, i) => (
            <motion.span
              key={line}
              aria-hidden
              className="inline sm:block"
              initial={{ opacity: 0, y: 20, filter: "blur(10px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{ duration: 1.1, ease: EASE, delay: 0.1 + i * 0.12 }}
            >
              {line}{" "}
            </motion.span>
          ))}
        </h1>

        <motion.div
          initial={{ opacity: 0, y: 10, filter: "blur(6px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 1, ease: EASE, delay: 0.42 }}
          className="mt-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"
        >
          <p className="max-w-[520px] text-[15px] leading-6 text-fg-3">{hero.subhead}</p>
          <a
            href={`${REPO}/issues/16`}
            target="_blank"
            rel="noreferrer"
            className="group inline-flex shrink-0 items-center gap-2 text-[15px] tracking-[-0.011em]"
          >
            <span className="font-[510] text-fg">{hero.badge}</span>
            <span className="text-fg-3 transition-colors group-hover:text-fg">{hero.badgeLink}</span>
            <Icon name="arrow" size={14} className="text-fg-3 transition-all duration-300 group-hover:translate-x-0.5 group-hover:text-fg" />
          </a>
        </motion.div>
      </Container>

      <motion.div
        initial={{ opacity: 0, y: 48 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1.4, ease: EASE, delay: 0.6 }}
        className="relative mx-auto mt-16 max-w-[1344px] px-2 sm:mt-[88px] sm:px-3"
      >
        <HeroApp />
        {/* fade the window into the page, like the fold on linear.app */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 bottom-0 h-[45%] bg-gradient-to-b from-transparent via-bg/70 to-bg"
        />
      </motion.div>
    </section>
  );
}
