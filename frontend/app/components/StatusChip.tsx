// Status chips — color-coded per the six Qloo envelope statuses + run phases.
const STATUS_STYLES: Record<string, string> = {
  ok: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  empty: "bg-zinc-500/15 text-zinc-300 border-zinc-500/40",
  needs_input: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  partial: "bg-sky-500/15 text-sky-300 border-sky-500/40",
  degraded: "bg-orange-500/15 text-orange-300 border-orange-500/40",
  error: "bg-red-500/15 text-red-300 border-red-500/40",
};

export function StatusChip({
  status,
  label,
}: {
  status: string;
  label?: string;
}) {
  const cls = STATUS_STYLES[status] ?? "bg-zinc-500/15 text-zinc-300 border-zinc-500/40";
  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${cls}`}
    >
      {label ?? status}
    </span>
  );
}
