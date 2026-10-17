import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cx } from "../../components/ui/primitives";
export const inputClass = "w-full rounded-lg border border-line-strong bg-bg px-3 py-2 text-sm text-fg disabled:opacity-50";
export function Panel({ title, children }: { title: string; children: ReactNode }) {
  return <section className="min-w-0 rounded-xl border border-line bg-elevated"><h2 className="border-b border-line px-4 py-3 font-semibold">{title}</h2><div className="space-y-4 p-4">{children}</div></section>;
}
export function Button({ primary, className, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { primary?: boolean }) {
  return <button type="button" className={cx("inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-40", primary ? "border-accent bg-accent text-on-brand hover:bg-accent-hover" : "border-line-strong bg-bg text-fg hover:bg-hover", className)} {...props} />;
}
export function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="flex min-w-0 flex-col gap-1.5 text-sm text-fg-2">{label}{children}</label>;
}
export function JsonView({ value }: { value: unknown }) {
  return <pre className="max-h-[36rem] overflow-auto whitespace-pre-wrap break-all rounded-lg bg-bg p-3 font-mono text-xs text-fg-2">{JSON.stringify(value, null, 2)}</pre>;
}
export function Note({ children }: { children: ReactNode }) { return <p className="text-sm leading-relaxed text-fg-3 [overflow-wrap:anywhere]">{children}</p>; }
