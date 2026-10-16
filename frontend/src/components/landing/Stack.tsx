import {
  siAmd,
  siGithubactions,
  siNodedotjs,
  siPydantic,
  siPython,
  siReact,
  siSqlite,
  siTailwindcss,
  siTypescript,
  siUv,
  siVite,
  siYaml,
  type SimpleIcon,
} from "simple-icons";
import { Reveal } from "../ui/motion";
import { cx, Section } from "../ui/primitives";

type Tech = { name: string; icon?: SimpleIcon; mono?: string };

/* What the merged code on main uses: requirements.txt, the workflow API (#17),
   hosted inference (#22), the frontend and CI. Tools that only appear in open PRs
   or later phases (fine-tuning, GPU serving) are left out until they merge. */
const rowA: Tech[] = [
  { name: "Python", icon: siPython },
  { name: "Pydantic", icon: siPydantic },
  { name: "openpyxl", mono: "xl" },
  { name: "ReportLab", mono: "RL" },
  { name: "Python HTTP API", mono: "API" },
  { name: "SQLite", icon: siSqlite },
  { name: "AMD Token Factory", icon: siAmd },
  { name: "DeepSeek-V4-Flash", mono: "DS" },
  { name: "uv", icon: siUv },
];

const rowB: Tech[] = [
  { name: "React", icon: siReact },
  { name: "TypeScript", icon: siTypescript },
  { name: "Vite", icon: siVite },
  { name: "Tailwind CSS", icon: siTailwindcss },
  { name: "Motion", mono: "M" },
  { name: "Node.js", icon: siNodedotjs },
  { name: "GitHub Actions", icon: siGithubactions },
  { name: "PyYAML", icon: siYaml },
  { name: "MaintIE", mono: "MI" },
];

function Chip({ t }: { t: Tech }) {
  return (
    <li className="group flex shrink-0 items-center gap-3 px-6 sm:px-8">
      {t.icon ? (
        <svg viewBox="0 0 24 24" width={26} height={26} aria-hidden className="shrink-0 fill-fg-3 transition-colors duration-300 group-hover:fill-fg">
          <path d={t.icon.path} />
        </svg>
      ) : (
        <span
          aria-hidden
          className="grid size-[26px] shrink-0 place-items-center rounded-[6px] border-[1.5px] border-fg-3 font-mono text-[10px] font-semibold text-fg-3 transition-colors duration-300 group-hover:border-fg group-hover:text-fg"
        >
          {t.mono}
        </span>
      )}
      <span className="text-[18px] font-[510] tracking-[-0.015em] whitespace-nowrap text-fg-3 transition-colors duration-300 group-hover:text-fg">
        {t.name}
      </span>
    </li>
  );
}

/** Infinite horizontal loop: the list is rendered twice and shifted by half its width. */
function Marquee({ items, reverse, seconds }: { items: Tech[]; reverse?: boolean; seconds: number }) {
  return (
    <div className="marquee group/m relative overflow-hidden py-3 [mask-image:linear-gradient(90deg,transparent,#000_8%,#000_92%,transparent)]">
      <div
        className={cx("marquee-track flex w-max group-hover/m:[animation-play-state:paused]", reverse && "marquee-reverse")}
        style={{ animationDuration: `${seconds}s` }}
      >
        {[0, 1].map((copy) => (
          <ul key={copy} className="flex" aria-hidden={copy === 1 || undefined}>
            {items.map((t) => (
              <Chip key={t.name} t={t} />
            ))}
          </ul>
        ))}
      </div>
    </div>
  );
}

export function Stack() {
  return (
    <Section
      eyebrow="Stack"
      title="Open tools and AMD inference"
      intro="Typed Python for ingestion, rules and reports, with extraction and cited drafts served by models on AMD Token Factory. The workspace preview on this page still runs on synthetic fixtures."
    >
      <Reveal className="-mx-4 space-y-6 sm:-mx-8">
        <Marquee items={rowA} seconds={42} />
        <Marquee items={rowB} seconds={38} reverse />
      </Reveal>
    </Section>
  );
}
