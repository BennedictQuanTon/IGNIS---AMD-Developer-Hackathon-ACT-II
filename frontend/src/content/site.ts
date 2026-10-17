// All landing-page copy and figures. Every number cites its source; see docs/design/LANDING_PAGE.md.

export const REPO = "https://github.com/khanhtuongnakitomo/IGNIS";

/** Set to a path under /public (for example "/screenshot-review.png") once a real capture exists. */
export const productScreenshot: { src: string; caption: string } | null = null;

/** Set once a demo deployment exists; the nav button stays hidden until then. */
export const demoUrl: string | null = null;

export const nav = [
  { id: "challenge", label: "Challenge" },
  { id: "problem", label: "Problem" },
  { id: "product", label: "Product" },
  { id: "comparison", label: "Comparison" },
  { id: "team", label: "Team" },
] as const;

export const hero = {
  headline: ["The evidence system for", "maintenance teams and AI"],
  subhead:
    "Purpose-built for turning messy work orders into reviewed records, code-computed priorities and cited reports.",
  badge: "ACT III",
  badgeLink: "AMD Developer Hackathon",
};

/** Problem figures from issue #21, checked against the cited reports on 16 Oct 2026.
    Keep each scope note: multiple-answer survey, one HVAC case, sector context only. */
export const problem = {
  lead: "Maintenance history is hard to trust.",
  rest: "Most teams spend over half their time firefighting, work-order text is often incomplete or inconsistent, and every unplanned hour is expensive. IGNIS makes that history checkable.",
  reactive: {
    rows: [
      { label: "Call preventive maintenance a core strategy", value: 71, display: "71%", gap: false },
      { label: "Spend most of their time on it", value: 35, display: "under 35%", gap: true },
      { label: "Spend over half their time on breakdowns", value: 58, display: "58%", gap: true },
    ],
    note: "n = 1,320 · US and Canada · vendor survey",
  },
  quality: {
    issues: 55,
    noVerb: 33,
    note: "one centrifugal pump · 8 years of work orders",
  },
  downtime: {
    rows: [
      { label: "Automotive, large plant", value: 2_300_000, display: "$2.3M" },
      { label: "Fast-moving consumer goods", value: 36_000, display: "$36K" },
    ],
    note: "181 interviews · data Apr 2019 – Mar 2023",
  },
  figures: [
    {
      fig: "FIG 2.1",
      title: "Teams still firefight",
      body: "In a 2025 survey of 1,320 maintenance professionals, 71% called preventive maintenance a core strategy, yet under 35% spend most of their time on it and 58% spend over half reacting to breakdowns.",
      source: {
        label: "MaintainX, 2025 State of Industrial Maintenance",
        href: "https://www.getmaintainx.com/newsroom/state-of-industrial-maintenance-report-2025",
      },
    },
    {
      fig: "FIG 2.2",
      title: "Work-order text is unreliable",
      body: "Analysing eight years of work orders for one centrifugal pump, researchers found data-quality issues in 55% of records, and 33% gave no verb for the work done.",
      source: {
        label: "Woods et al., Semantic Web 15(2), 2024",
        href: "https://doi.org/10.3233/SW-233299",
      },
    },
    {
      fig: "FIG 2.3",
      title: "Every unplanned hour is expensive",
      body: "One hour of unplanned downtime is estimated to cost a large automotive plant $2.3 million and a consumer-goods plant $36,000.",
      source: {
        label: "Siemens, The True Cost of Downtime 2024, pp. 2–4",
        href: "https://assets.new.siemens.com/siemens/assets/api/uuid:1b43afb5-2d07-47f7-9eb7-893fe7d0bc59/TCOD-2024_original.pdf",
      },
    },
  ],
  disclaimer: "These figures describe the problem. They are not savings or accuracy measured with IGNIS.",
};

export const challenge = {
  title: "AMD Developer Hackathon: ACT III",
  intro:
    "A hybrid build event on lablab.ai, online 12–18 October 2026, with an on-site final phase in Italy for selected teams. AMD technology must be part of the working product.",
  stats: [
    { value: 7, suffix: " days", label: "Online build, 12–18 Oct 2026" },
    { value: 17000, prefix: "$", suffix: "+", label: "Prize pool" },
    { value: 5, label: "Tracks (4 themed + Evolus)" },
    { value: 4, label: "Judging criteria" },
  ],
  criteria: ["Application of Technology", "Presentation", "Business Value", "Originality"],
};

export const track = {
  title: "Track 1 · Intelligent Industry",
  quote: "Help factories spot problems earlier and operate better.",
  problem: "The problem is knowing what matters and what to do next.",
  coverage: [
    { source: "Maintenance reports", status: "now", note: "In scope now" },
    { source: "Technical manuals", status: "now", note: "In scope now — applicable passages only" },
    { source: "Sensors", status: "roadmap", note: "Roadmap" },
    { source: "Machines / logs", status: "roadmap", note: "Roadmap" },
    { source: "Cameras", status: "out", note: "Out of scope" },
  ] as const,
  problems: [
    { title: "Messy text", body: "Work orders are short, inconsistent and full of equipment shorthand." },
    {
      title: "Fluent but wrong",
      body: "A generated report can miscount, attach the wrong fault or cite the wrong machine's manual.",
    },
    { title: "No trail", body: "Without links back to source records, nobody can check or sign a conclusion." },
  ],
};

export type Owner = "AI" | "CODE" | "HUMAN";

export const product = {
  title: "An evidence desk for maintenance teams",
  intro:
    "Models propose. Code computes. People approve. Every claim in the final report resolves to a fact, a passage and an original record.",
  flow: [
    { label: "Upload export", owner: "CODE" },
    { label: "Extract entities", owner: "AI" },
    { label: "Review", owner: "HUMAN" },
    { label: "Facts & alerts", owner: "CODE" },
    { label: "Applicable evidence", owner: "CODE" },
    { label: "Cited draft", owner: "AI" },
    { label: "Expert sign-off → Report", owner: "HUMAN" },
  ] as { label: string; owner: Owner }[],
  analogy:
    "Think of it as a hospital for machines. The model is the clerk and the drafting assistant. The maintenance expert is the responsible doctor.",
  analogyHref: `${REPO}/blob/main/artifacts/ignis-architecture-explained.html`,
};

export const features = [
  {
    icon: "upload",
    title: "Export intake",
    body: "Reads CSV, XLSX and JSON exports, records file hashes and asks a person to confirm column mapping.",
  },
  {
    icon: "spans",
    title: "Span-level extraction",
    body: "Fixture suggestions are anchored to exact text spans. Hosted AMD inference is planned and is not connected to this preview.",
  },
  {
    icon: "review",
    title: "Human review gate",
    body: "Accept, correct or reject each record. Nothing counts until a named reviewer approves it.",
  },
  {
    icon: "calc",
    title: "Code-computed priority",
    body: "Severity × recurrence × criticality, versioned rules. Not a failure probability.",
  },
  {
    icon: "filter",
    title: "Scoped evidence",
    body: "An applicability graph excludes wrong-model and superseded manuals before retrieval picks the top 3 passages.",
  },
  {
    icon: "report",
    title: "Checked report",
    body: "Numbers render from typed facts; claims that cite nothing retrieved are rejected before the PDF.",
  },
] as const;

export const delivered = [
  {
    value: 9,
    label: "Hash-chained pipeline stages, each persisted before the next starts",
    source: "ignis_wo/pipeline.py · PR #15",
    visual: "chain",
  },
  { value: 56, label: "Automated tests in the merged baseline", source: "tests/ · PR #15", visual: "none" },
  {
    value: 1076,
    label: "Expert-annotated MaintIE work orders, pinned by revision and SHA-256",
    source: "maintie_split_lock.json",
    visual: "split",
  },
  {
    value: 224,
    secondary: 7,
    label: "Entity types · relation types enforced by the extraction schema",
    source: "maintie_labels_v1.json",
    visual: "none",
  },
] as const;

export const maintieSplit = [
  { name: "train", count: 860 },
  { name: "dev", count: 108 },
  { name: "test", count: 108 },
];

export const benchmarkMetrics = ["Extraction F1", "Schema validity", "p50 / p95 latency", "Valid outputs / min"];

export type Cell = "yes" | "no" | "partial" | "na" | "progress";

export const comparison = {
  columns: ["Generic LLM chat", "Plain RAG assistant", "Spreadsheet / CMMS report", "IGNIS"],
  rows: [
    { capability: "Numbers computed by code", cells: ["no", "no", "yes", "yes"] },
    { capability: "Human approval before a record counts", cells: ["no", "no", "partial", "yes"] },
    { capability: "Every claim links to a source record", cells: ["no", "partial", "no", "yes"] },
    { capability: "Excludes wrong-model / superseded manuals", cells: ["no", "no", "na", "progress"] },
    { capability: "Abstains when evidence is missing", cells: ["no", "partial", "na", "progress"] },
    { capability: "Labels real vs synthetic, live vs replay", cells: ["no", "no", "no", "yes"] },
    { capability: "Reads free-text work orders", cells: ["yes", "yes", "no", "yes"] },
  ] as { capability: string; cells: Cell[] }[],
  footnote:
    "Columns describe typical default behaviour of each approach, not specific products. “In progress” items are designed and assigned in issue #17.",
};

export const team = {
  name: "Team Develarper",
  members: [
    {
      name: "Khanh Tuong Huynh",
      initials: "KT",
      role: "Team Lead · AI Engineer",
      github: "khanhtuongnakitomo",
      owns: "Backend pipeline, review data, alerts, retrieval and evidence-linked reports",
      photo: { src: "/team/khanh-tuong-huynh.jpg", origin: "50% 38%", scale: 1 },
    },
    {
      name: "Long Quan Ton",
      initials: "LQ",
      role: "AI Engineer · Frontend Developer",
      github: "BennedictQuanTon",
      owns: "UI/UX, frontend, demo video and independent end-to-end evaluation",
      photo: { src: "/team/long-quan-ton.jpg", origin: "50% 30%", scale: 1 },
    },
    {
      name: "Yoshio Nomura",
      initials: "YN",
      role: "AI Engineer · LLMOps",
      github: "UniverseScripts",
      owns: "AMD API integration, MaintIE prompts and model quality/latency benchmarks",
      photo: { src: "/team/yoshio-nomura.jpg", origin: "46% 22%", scale: 1 },
    },
  ],
};

export const sources = [
  {
    label: "Challenge",
    text: "AMD Developer Hackathon ACT III, lablab.ai",
    href: "https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii",
  },
  {
    label: "Survey",
    text: "MaintainX, 2025 State of Industrial Maintenance",
    href: "https://www.getmaintainx.com/newsroom/state-of-industrial-maintenance-report-2025",
  },
  {
    label: "Study",
    text: "Woods et al., ontology for maintenance data quality (2024)",
    href: "https://doi.org/10.3233/SW-233299",
  },
  {
    label: "Downtime",
    text: "Siemens, The True Cost of Downtime 2024",
    href: "https://assets.new.siemens.com/siemens/assets/api/uuid:1b43afb5-2d07-47f7-9eb7-893fe7d0bc59/TCOD-2024_original.pdf",
  },
  { label: "Dataset", text: "MaintIE repository (MIT), revision 825e771", href: "https://github.com/nlp-tlp/maintie" },
  { label: "Paper", text: "MaintIE, LREC-COLING 2024", href: "https://aclanthology.org/2024.lrec-main.954.pdf" },
  {
    label: "AMD API",
    text: "Radeon Cloud chat completions docs",
    href: "https://amd-aim.github.io/radeon-cloud-docs/api/chat-completions/",
  },
  { label: "Proposal", text: "Issue #16, API-based project proposal", href: `${REPO}/issues/16` },
  { label: "Backend", text: "Issue #17, backend mission", href: `${REPO}/issues/17` },
  { label: "Models", text: "Issue #18, model mission", href: `${REPO}/issues/18` },
  { label: "Frontend", text: "Issue #19, frontend mission", href: `${REPO}/issues/19` },
  { label: "Pipeline", text: "PR #15, deterministic work-order pipeline", href: `${REPO}/pull/15` },
  { label: "Architecture", text: "Proposed system workflow", href: `${REPO}/blob/main/docs/PROPOSED_SYSTEM_WORKFLOW.md` },
];
