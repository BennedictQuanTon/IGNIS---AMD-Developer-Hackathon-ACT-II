import { motion, useReducedMotion } from "motion/react";
import { pillars, statement, strip } from "../../content/site";
import { EASE, Reveal, Stagger, StaggerItem } from "../ui/motion";
import { Container, cx } from "../ui/primitives";

/* Strip: event facts set like a logo row ------------------------------------- */

export function Strip() {
  return (
    <section className="pt-10 pb-24 sm:pb-32">
      <Container>
        <Stagger className="grid grid-cols-2 items-center gap-x-6 gap-y-6 sm:grid-cols-3 lg:grid-cols-6">
          {strip.items.map((item) => (
            <StaggerItem key={item}>
              <span className="block text-[20px] font-[590] tracking-[-0.02em] whitespace-nowrap text-fg/90 sm:text-[22px]">
                {item}
              </span>
            </StaggerItem>
          ))}
        </Stagger>
        <Reveal className="mt-14">
          <p className="t-label">{strip.caption}</p>
        </Reveal>
      </Container>
    </section>
  );
}

/* Statement: white lead sentence, grey continuation ---------------------------- */

export function Statement() {
  return (
    <section className="pb-24 sm:pb-36">
      <Container>
        <Reveal>
          <h2 className="t-h2 max-w-[1250px]">
            <span className="text-fg">{statement.lead}</span> <span className="text-fg-3">{statement.rest}</span>
          </h2>
        </Reveal>
      </Container>
    </section>
  );
}

/* Figures: three isometric line drawings, like Linear's FIG 0.x -------------- */

type P3 = [number, number, number];
const S = 1;
const iso = ([x, y, z]: P3, ox = 200, oy = 150): [number, number] => [
  ox + (x - y) * 0.866 * S,
  oy + (x + y) * 0.5 * S - z * S,
];
const path = (pts: P3[], ox?: number, oy?: number) =>
  pts.map((p, i) => `${i ? "L" : "M"}${iso(p, ox, oy).map((n) => n.toFixed(1)).join(" ")}`).join(" ") + " Z";

function boxFaces([x, y, z]: P3, [w, d, h]: P3, ox?: number, oy?: number) {
  return {
    top: path([[x, y, z + h], [x + w, y, z + h], [x + w, y + d, z + h], [x, y + d, z + h]], ox, oy),
    right: path([[x + w, y, z], [x + w, y + d, z], [x + w, y + d, z + h], [x + w, y, z + h]], ox, oy),
    left: path([[x, y + d, z], [x + w, y + d, z], [x + w, y + d, z + h], [x, y + d, z + h]], ox, oy),
  };
}

function IsoBox({
  at,
  size,
  delay = 0,
  hot,
  float,
  children,
}: {
  at: P3;
  size: P3;
  delay?: number;
  hot?: boolean;
  float?: number;
  children?: React.ReactNode;
}) {
  const reduce = useReducedMotion();
  const f = boxFaces(at, size);
  const stroke = hot ? "#FFC400" : "rgb(255 255 255 / 0.32)";
  const draw = {
    initial: { pathLength: 0, fillOpacity: 0 },
    whileInView: { pathLength: 1, fillOpacity: 1 },
    viewport: { once: true, margin: "-60px" },
    transition: { pathLength: { duration: 1.4, ease: EASE, delay }, fillOpacity: { duration: 0.6, delay: delay + 0.5 } },
  };
  return (
    <motion.g
      animate={float && !reduce ? { y: [0, -float, 0] } : undefined}
      transition={float ? { duration: 4, repeat: Infinity, ease: "easeInOut", delay: delay + 1.5 } : undefined}
    >
      {(["left", "right", "top"] as const).map((face) => (
        <motion.path
          key={face}
          d={f[face]}
          fill="#0b0b0c"
          stroke={stroke}
          strokeWidth={1}
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
          {...draw}
        />
      ))}
      {children}
    </motion.g>
  );
}

/** FIG 0.1 — stacked work-order slabs; the top slab carries extracted lines. */
function FigPropose() {
  const layers = [0, 1, 2, 3, 4];
  return (
    <svg viewBox="0 0 400 300" className="w-full overflow-visible" aria-hidden>
      <g transform="translate(0 40)">
      {layers.map((i) => (
        <IsoBox key={i} at={[-80, -80, i * 16]} size={[160, 160, 10]} delay={i * 0.12} float={i === 4 ? 6 : undefined}>
          {i === 4 &&
            [0, 1, 2, 3].map((l) => (
              <motion.path
                key={l}
                d={path([[-55, -50 + l * 26, 4 * 16 + 10], [-55 + (l % 2 ? 70 : 110), -50 + l * 26, 4 * 16 + 10]]).replace(" Z", "")}
                stroke={l === 1 ? "#FFC400" : "rgb(255 255 255 / 0.45)"}
                strokeWidth={1.5}
                strokeLinecap="round"
                fill="none"
                initial={{ pathLength: 0 }}
                whileInView={{ pathLength: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, ease: EASE, delay: 1.2 + l * 0.15 }}
              />
            ))}
        </IsoBox>
      ))}
      </g>
    </svg>
  );
}

/** FIG 0.2 — modular blocks; one lifts with a yellow top (the computed fact). */
function FigCompute() {
  const blocks: { at: P3; size: P3; hot?: boolean; float?: number }[] = [
    { at: [-20, -110, 0], size: [70, 70, 60] },
    { at: [-110, -20, 0], size: [70, 70, 60] },
    { at: [-20, -20, 0], size: [70, 70, 40] },
    { at: [60, -20, 0], size: [60, 70, 40] },
    { at: [-20, 60, 0], size: [70, 60, 30], hot: true, float: 10 },
  ];
  return (
    <svg viewBox="0 0 400 300" className="w-full" aria-hidden>
      <g transform="translate(0 30)">
        {blocks.map((b, i) => (
          <IsoBox key={i} at={b.at} size={b.size} hot={b.hot} float={b.float} delay={i * 0.12} />
        ))}
      </g>
    </svg>
  );
}

/** FIG 0.3 — a row of review cards; the front one is the approved record. */
function FigApprove() {
  const cards = [0, 1, 2, 3, 4, 5, 6, 7];
  return (
    <svg viewBox="0 0 400 300" className="w-full" aria-hidden>
      <g transform="translate(10 60)">
        {cards.map((i) => (
          <IsoBox key={i} at={[-60, -90 + i * 18, 0]} size={[120, 4, 132 - i * 12]} delay={i * 0.08} hot={i === 0} />
        ))}
        <motion.path
          d={path([[-25, -86, 112], [-8, -86, 100], [28, -86, 128]]).replace(" Z", "")}
          stroke="#FFC400"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          initial={{ pathLength: 0 }}
          whileInView={{ pathLength: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: EASE, delay: 1.6 }}
        />
      </g>
    </svg>
  );
}

const FIGS = [FigPropose, FigCompute, FigApprove];

export function Figures() {
  return (
    <section className="pb-24 sm:pb-32">
      <Container>
        <div className="grid border-line md:grid-cols-3">
          {pillars.map((p, i) => {
            const Fig = FIGS[i];
            return (
              <Reveal
                key={p.fig}
                delay={i * 0.1}
                className={cx(
                  "flex flex-col border-line py-8 md:py-0",
                  i > 0 && "border-t md:border-t-0 md:border-l md:pl-8",
                  i < 2 && "md:pr-8",
                )}
              >
                <p className="t-label">{p.fig}</p>
                <div className="my-6 flex flex-1 items-center justify-center md:my-10">
                  <div className="w-full max-w-[340px]">
                    <Fig />
                  </div>
                </div>
                <h3 className="text-[15px] leading-6 font-[510] text-fg">{p.title}</h3>
                <p className="mt-1 max-w-[368px] text-[15px] leading-6 text-fg-3">{p.body}</p>
              </Reveal>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
