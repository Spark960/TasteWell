"use client";

import { useEffect, useState } from "react";

import type { Brief, Candidate, Evidence, TraceEvent } from "@/lib/api";
import { StatusChip } from "./StatusChip";
import { LiveTrace } from "./TracePanel";

/** Ticking clock for an in-flight run; startedAt comes from the run event. */
function RunningFor({ startedAt }: { startedAt: number }) {
  const [secs, setSecs] = useState(0);
  useEffect(() => {
    const h = setInterval(
      () => setSecs(Math.max(1, Math.floor((Date.now() - startedAt) / 1000))),
      1000,
    );
    return () => clearInterval(h);
  }, [startedAt]);
  return (
    <span className="text-[11px] tabular-nums text-zinc-400">
      running… {Math.max(1, secs)}s
    </span>
  );
}

const CITE_RE = /\s*\((?:ids?:([^)]+))\)\s*$/;

/** Split "(id:…)" citations off the end of a recommendation string. */
function splitCitations(s: string): { text: string; ids: string[] } {
  let text = s;
  let ids: string[] = [];
  let m = text.match(CITE_RE);
  while (m) {
    ids = ids.concat(m[1].split(/\s*[,;]\s*/).filter(Boolean));
    text = text.slice(0, m.index ?? 0);
    m = text.match(CITE_RE);
  }
  return { text, ids };
}

function evidenceFor(ev: Evidence[], ids: string[]): Evidence | undefined {
  for (const id of ids) {
    const hit = ev.find((e) => (e.ids ?? []).includes(id));
    if (hit) return hit;
  }
  return undefined;
}

function ProvenanceTip({ evidence }: { evidence: Evidence }) {
  return (
    <span className="group relative inline-flex">
      <StatusChip
        status={evidence.status ?? "ok"}
        label={evidence.operation ?? evidence.tool ?? "qloo"}
      />
      <span className="pointer-events-none absolute bottom-full left-0 z-20 mb-1 hidden w-64 rounded-md border border-zinc-700 bg-zinc-900 p-2 text-[10px] leading-relaxed text-zinc-300 shadow-lg group-hover:block">
        <span className="font-semibold text-zinc-100">
          {evidence.tool ?? "qloo"} · {evidence.status}
        </span>
        {evidence.result_count != null && (
          <span> · {evidence.result_count} results</span>
        )}
        {evidence.summary && (
          <span className="mt-1 block text-zinc-400">{evidence.summary}</span>
        )}
      </span>
    </span>
  );
}

function Section({
  title,
  items,
  evidence,
}: {
  title: string;
  items: string[];
  evidence: Evidence[];
}) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
        {title}
      </h3>
      <ul className="space-y-1.5">
        {items.map((raw, i) => {
          const { text, ids } = splitCitations(raw);
          const ev = ids.length > 0 ? evidenceFor(evidence, ids) : undefined;
          return (
            <li
              key={i}
              className="flex items-start gap-2 text-sm leading-relaxed text-zinc-200"
            >
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-teal-400/70" />
              <span className="min-w-0 flex-1">{text}</span>
              {ev && <ProvenanceTip evidence={ev} />}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function CandidatePicker({
  reason,
  candidates,
  onPick,
}: {
  reason: string;
  candidates: Candidate[];
  onPick: (c: Candidate) => void;
}) {
  return (
    <div
      role="dialog"
      aria-label="Disambiguation picker"
      className="rounded-lg border border-amber-500/40 bg-amber-500/5 p-3"
    >
      <p className="mb-2 text-xs leading-relaxed text-amber-200">
        <span className="font-semibold">Ambiguous match.</span> {reason}
      </p>
      <div className="space-y-1.5">
        {candidates.map((c) => {
          const type = (c.type ?? "").split(":").pop() ?? "";
          return (
            <button
              key={c.id}
              type="button"
              onClick={() => onPick(c)}
              className="flex w-full items-center justify-between rounded-md border border-amber-500/30 bg-zinc-900/80 px-3 py-2 text-left text-sm text-zinc-200 transition hover:border-amber-400 hover:bg-amber-500/10"
            >
              <span className="min-w-0">
                <span className="truncate font-medium">{c.name ?? c.id}</span>
                {type && (
                  <span className="ml-2 text-xs text-zinc-500">{type}</span>
                )}
              </span>
              {c.popularity != null && (
                <span className="ml-3 shrink-0 text-xs tabular-nums text-zinc-500">
                  {Math.round(c.popularity * 100)}% match
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function ResultPane({
  mode,
  phase,
  brief,
  error,
  needsInput,
  startedAt,
  events,
  onPick,
}: {
  mode: "grounded" | "generic";
  phase: string;
  brief: Brief | null;
  error: string | null;
  needsInput: { reason: string; candidates: Candidate[] } | null;
  startedAt: number | null;
  events: TraceEvent[];
  onPick: (c: Candidate) => void;
}) {
  const grounded = mode === "grounded";
  const title = grounded ? "Grounded" : "Ungrounded";
  const sub = grounded ? "Qloo taste data on" : "Qloo off, model only";

  return (
    <section
      aria-label={`${title} result`}
      className={`flex min-h-0 flex-col rounded-xl border p-4 ${
        grounded
          ? "border-teal-500/30 bg-teal-500/[0.03]"
          : "border-zinc-800 bg-zinc-900/40"
      }`}
    >
      <header className="mb-3 flex items-center justify-between gap-2">
        <div>
          <h2
            className={`text-sm font-semibold ${
              grounded ? "text-teal-300" : "text-zinc-300"
            }`}
          >
            {title}
          </h2>
          <p className="text-[11px] text-zinc-500">{sub}</p>
        </div>
        {phase === "running" && startedAt !== null && (
          <RunningFor startedAt={startedAt} />
        )}
        {phase === "needs_input" && <StatusChip status="needs_input" />}
        {phase === "done" && brief?.evidence && brief.evidence.length > 0 && (
          <span className="text-[11px] text-zinc-500">
            {brief.evidence.length} Qloo envelopes
          </span>
        )}
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto" aria-live="polite">
        {phase === "idle" && (
          <p className="text-sm text-zinc-600">Nothing yet. Run a brief.</p>
        )}

        {phase === "starting" && events.length === 0 && (
          <div className="space-y-2">
            <div className="h-3 w-2/3 animate-pulse rounded bg-zinc-800" />
            <div className="h-3 w-full animate-pulse rounded bg-zinc-800" />
            <div className="h-3 w-4/5 animate-pulse rounded bg-zinc-800" />
          </div>
        )}

        {(phase === "running" || (phase === "starting" && events.length > 0)) &&
          events.length > 0 && <LiveTrace events={events} pane={mode} />}

        {error && (
          <div
            role="alert"
            className="rounded-md border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200"
          >
            <span className="font-semibold">Run error.</span> {error}
          </div>
        )}

        {needsInput && (
          <CandidatePicker
            reason={needsInput.reason}
            candidates={needsInput.candidates}
            onPick={onPick}
          />
        )}

        {brief && !error && (
          <div className="space-y-4">
            {brief.audience_profile && (
              <p className="text-sm leading-relaxed text-zinc-100">
                {splitCitations(brief.audience_profile).text}
              </p>
            )}
            <Section
              title="Menu tilt"
              items={brief.menu_tilt ?? []}
              evidence={brief.evidence ?? []}
            />
            <Section
              title="Music & programming"
              items={brief.music_programming ?? []}
              evidence={brief.evidence ?? []}
            />
            <Section
              title="Adjacent brands"
              items={brief.adjacent_brands ?? []}
              evidence={brief.evidence ?? []}
            />
            <Section
              title="Tag themes"
              items={brief.tag_themes ?? []}
              evidence={brief.evidence ?? []}
            />
            {needsInput === null && (brief.honest_absences?.length ?? 0) > 0 && (
              <div className="rounded-md border border-zinc-800 bg-zinc-900/60 p-2.5">
                <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
                  No grounded result
                </h3>
                <ul className="space-y-1">
                  {brief.honest_absences!.map((a, i) => (
                    <li key={i} className="text-xs text-zinc-500">
                      Left blank rather than guessed: {a}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {!grounded && (brief.audience_profile || (brief.menu_tilt?.length ?? 0) > 0) && (
              <p className="rounded-md border border-zinc-800 bg-zinc-900/60 p-2.5 text-[11px] leading-relaxed text-zinc-500">
                No Qloo data here. These are the model&apos;s own guesses.
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
