"use client";

import { useState } from "react";

export type Preset = {
  label: string;
  brief: string;
  region: string;
  audience: string;
};

const PRESETS: Preset[] = [
  {
    label: "Natural wine bar · millennials · Brooklyn",
    brief: "natural wine bar",
    region: "Brooklyn",
    audience: "millennials",
  },
  {
    label: "Taco shop · families · Texas",
    brief: "taco shop",
    region: "Texas",
    audience: "families",
  },
  {
    label: "Listening bar · young professionals · Williamsburg",
    brief: "listening bar",
    region: "Williamsburg",
    audience: "young professionals",
  },
];

export function BriefForm({
  running,
  onRun,
  onCancel,
}: {
  running: boolean;
  onRun: (p: { brief: string; region: string; audience: string }) => void;
  onCancel: () => void;
}) {
  const [brief, setBrief] = useState("");
  const [region, setRegion] = useState("");
  const [audience, setAudience] = useState("");
  const valid = brief.trim().length > 0;

  return (
    <form
      aria-label="Venue brief"
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        if (valid && !running) onRun({ brief, region, audience });
      }}
    >
      <div>
        <div className="mb-1.5 flex flex-wrap gap-1.5">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              type="button"
              disabled={running}
              onClick={() => {
                setBrief(p.brief);
                setRegion(p.region);
                setAudience(p.audience);
              }}
              className="rounded-full border border-zinc-700 bg-zinc-800/60 px-2.5 py-1 text-[11px] text-zinc-300 transition hover:border-teal-500/60 hover:text-teal-200 disabled:opacity-40"
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label
          htmlFor="brief"
          className="mb-1 block text-xs font-medium text-zinc-400"
        >
          Venue concept
        </label>
        <input
          id="brief"
          value={brief}
          onChange={(e) => setBrief(e.target.value)}
          placeholder="e.g. natural wine bar"
          className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-teal-500 focus:outline-none"
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label
            htmlFor="region"
            className="mb-1 block text-xs font-medium text-zinc-400"
          >
            Region / catchment
          </label>
          <input
            id="region"
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            placeholder="e.g. Brooklyn"
            className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-teal-500 focus:outline-none"
          />
        </div>
        <div>
          <label
            htmlFor="audience"
            className="mb-1 block text-xs font-medium text-zinc-400"
          >
            Target audience
          </label>
          <input
            id="audience"
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
            placeholder="e.g. millennials"
            className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-teal-500 focus:outline-none"
          />
        </div>
      </div>

      {running ? (
        <button
          type="button"
          onClick={onCancel}
          className="w-full rounded-md border border-red-500/50 bg-red-500/10 px-3 py-2 text-sm font-medium text-red-300 transition hover:bg-red-500/20"
        >
          Stop run
        </button>
      ) : (
        <button
          type="submit"
          disabled={!valid}
          className="w-full rounded-md bg-teal-500 px-3 py-2 text-sm font-semibold text-zinc-950 transition hover:bg-teal-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Run both panes
        </button>
      )}
      <p className="text-[11px] leading-relaxed text-zinc-500">
        Each brief runs twice - with Qloo taste data, and without.
      </p>
    </form>
  );
}
