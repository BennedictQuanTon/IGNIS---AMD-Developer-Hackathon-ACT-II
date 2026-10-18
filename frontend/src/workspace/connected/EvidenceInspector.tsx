import { useEffect, useRef } from "react";
import type { Run } from "./api";
import { resolveReference } from "./workflow";
import { Button, JsonView, Note } from "./ui";

export function EvidenceInspector({ run, reference, onClose, inspect }: { run: Run | null; reference: string | null; onClose: () => void; inspect: (id: string) => void }) {
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    if (!reference) return;
    const previous = document.activeElement as HTMLElement | null;
    document.getElementById("close-evidence-inspector")?.focus();
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") close.current(); };
    window.addEventListener("keydown", onKey);
    return () => { window.removeEventListener("keydown", onKey); previous?.focus(); };
  }, [reference]);
  if (!reference) return null;
  const selected = run ? resolveReference(run, reference) : null;
  return <div className="fixed inset-0 z-50 flex justify-end bg-black/70" onClick={onClose}>
    <aside role="dialog" aria-modal="true" aria-label="Evidence inspector" className="h-full w-full max-w-xl overflow-auto border-l border-line bg-elevated p-5" onClick={event => event.stopPropagation()}
      onKeyDown={event => { if (event.key !== "Tab") return; const controls = event.currentTarget.querySelectorAll<HTMLElement>("button, a[href], summary, [tabindex='0']"); const first = controls[0], last = controls[controls.length - 1]; if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); } else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); } }}>
      <Button id="close-evidence-inspector" onClick={onClose}>Close inspector</Button>
      <h2 className="my-4 break-all text-xl">{selected?.title || reference}</h2>
      {selected ? <><JsonView value={selected.value} /><div className="mt-4 flex flex-wrap gap-2">{selected.records.map(id => <Button key={id} onClick={() => inspect(id)}>Open source {id}</Button>)}</div></> : <Note>This reference is unavailable in the current saved snapshot. Reload or inspect the relevant historical PDF.</Note>}
    </aside>
  </div>;
}
