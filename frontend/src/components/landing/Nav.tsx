import { useEffect, useState } from "react";
import { AnimatePresence, motion, useMotionValueEvent, useScroll } from "motion/react";
import { demoUrl, nav, REPO } from "../../content/site";
import { Icon } from "../ui/icons";
import { ButtonLink, Container, cx, Wordmark } from "../ui/primitives";
import { EASE } from "../ui/motion";

export function Nav() {
  const { scrollY } = useScroll();
  const [scrolled, setScrolled] = useState(false);
  const [active, setActive] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  useMotionValueEvent(scrollY, "change", (y) => setScrolled(y > 8));

  // Scroll spy: the section crossing the upper third of the viewport is active.
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries)
          if (entry.isIntersecting) setActive(entry.target.id === "top" ? null : entry.target.id);
      },
      { rootMargin: "-30% 0px -65% 0px" },
    );
    const hero = document.getElementById("top");
    if (hero) observer.observe(hero);
    for (const item of nav) {
      const el = document.getElementById(item.id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, []);

  return (
    <motion.header
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.8, ease: EASE }}
      className={cx(
        "fixed inset-x-0 top-0 z-50 h-[73px] border-b transition-[background-color,border-color] duration-300",
        scrolled || open ? "border-line bg-bg/75 backdrop-blur-xl backdrop-saturate-150" : "border-transparent",
      )}
    >
      <Container className="flex h-full items-center justify-between">
        <a href="#top" aria-label="IGNIS home" className="-ml-1 flex h-8 items-center px-1">
          <Wordmark height={19} />
        </a>

        <div className="hidden items-center md:flex">
          <nav aria-label="Sections">
            <ul className="flex items-center">
              {nav.map((item) => (
                <li key={item.id}>
                  <a
                    href={`#${item.id}`}
                    className={cx(
                      "block px-3 py-1.5 text-[13px] tracking-normal transition-colors duration-150",
                      active === item.id ? "text-fg" : "text-fg-3 hover:text-fg",
                    )}
                  >
                    {item.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
          <span aria-hidden className="mx-4 h-4 w-px bg-line-strong" />
          <WorkspaceLink />
          {demoUrl ? (
            <ButtonLink href={demoUrl} external variant="light" className="ml-2">
              View demo
            </ButtonLink>
          ) : (
            <ButtonLink href={REPO} external variant="light" className="ml-2">
              GitHub
            </ButtonLink>
          )}
        </div>

        <button
          type="button"
          className="grid size-9 place-items-center rounded-[var(--radius)] text-fg-2 hover:bg-hover md:hidden"
          aria-expanded={open}
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          <Icon name={open ? "close" : "menu"} />
        </button>
      </Container>

      <AnimatePresence>
        {open && (
          <motion.nav
            aria-label="Sections"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="border-b border-line bg-bg/95 backdrop-blur-xl md:hidden"
          >
            <Container className="flex flex-col py-3">
              {nav.map((n) => (
                <a key={n.id} href={`#${n.id}`} onClick={() => setOpen(false)} className="py-2.5 text-[15px] text-fg-2 hover:text-fg">
                  {n.label}
                </a>
              ))}
              <WorkspaceLink className="px-0 py-2.5 text-[15px] text-fg-2" onClick={() => setOpen(false)} />
              <a href={REPO} target="_blank" rel="noreferrer" className="py-2.5 text-[15px] text-fg-2 hover:text-fg">
                GitHub
              </a>
            </Container>
          </motion.nav>
        )}
      </AnimatePresence>
    </motion.header>
  );
}

/** The one route into the product, so it reads as a destination rather than another section link. */
function WorkspaceLink({ className, onClick }: { className?: string; onClick?: () => void }) {
  return (
    <a href="#/app" onClick={onClick} className={cx("px-3 py-1.5 text-[13px] tracking-normal text-fg-3 transition-colors hover:text-fg", className)}>
      Workspace
    </a>
  );
}
