"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { API_BASE } from "@/lib/api";
import { parseVenueCsv } from "./venueCsv";
import { sampleDecision } from "./sampleDecision";
import "./decision.css";

type Evidence = {
  id: string; operation: string; status: string; source_id: string | null;
  name: string | null; affinity: number | null; query: Record<string, unknown>;
  correlation_id: string | null; retrieved_at: string; summary: string | null;
};
type Option = {
  id: string; title: string; description: string; format: string;
  evidence_ids: string[]; unknowns: string[]; constraint_notes: string[];
  artist_rank: number | null;
  venue_ranks: Record<string, number | null>;
};
type Venue = {
  id: string; name: string; region: string;
  live_music_allowed: boolean; budget_limit: number | null;
};
type Scenario = {
  id: string; venue_id: string; status: "ready" | "no_evidence";
  original_query: Record<string, unknown>; changed_query: Record<string, unknown>;
  artist_ids: string[]; artist_names: Record<string, string>;
  baseline_ranks: Record<string, number | null>;
  scenario_ranks: Record<string, number | null>;
  evidence_ids: string[]; note: string; created_at: string;
};
type AgentReview = {
  id: string; status: "recommend" | "needs_input" | "abstain";
  snapshot_fingerprint: string; source_mode: "live" | "replay";
  option_id: string | null; venue_id: string | null; evidence_ids: string[];
  scenario_id: string | null; rationale: string; alternatives: string[];
  unknowns: string[]; next_check: string; reason: string;
  actions: { tool: string; arguments: Record<string, unknown>; outcome: string;
    evidence_ids: string[]; scenario_id: string | null }[];
};
export type Decision = {
  id: string; status: "ready" | "needs_input" | "no_evidence" | "blocked";
  source_mode?: "live" | "replay" | "sample"; replay_of?: string | null;
  candidates: { id: string; name?: string; type?: string }[];
  options: Option[]; evidence: Evidence[]; notes: string[];
  selected_option_id: string | null; selected_at: string | null;
  pilot_plan: PilotPlan | null;
  outcome: PilotOutcome | null;
  venues: Venue[];
  resolution_kind: "tag" | "artist" | null;
  resolution_key: string | null;
  request?: { audience: string };
  scenarios?: Scenario[];
  snapshot_fingerprint?: string;
  agent_reviews?: AgentReview[];
};
type PilotPlan = {
  venue_id: string;
  owner: string; target_date: string; success_measure: string;
  baseline: string; cost_assumption: string; next_action: string;
};
type PilotOutcome = {
  metric: string; baseline_value: number; actual_value: number;
  unit: string; period: string; source: string; notes: string;
};
type SavedDecision = {
  id: string; venue_name: string; concept: string; region: string;
  status: string; source_mode?: "live" | "replay"; selected_option_id: string | null;
  has_outcome: boolean; updated_at: string;
};
type Form = {
  venue_name: string; concept: string; region: string; audience: string;
  objective: string; budget_limit: string; live_music_allowed: boolean;
};
const initial: Form = {
  venue_name: "", concept: "", region: "", audience: "",
  objective: "Choose a weekly programming pilot", budget_limit: "",
  live_music_allowed: true,
};

function describeTagChoice(id: string, name: string) {
  const tag = id.toLowerCase();
  if (tag.includes(":category:place:")) return { label: "Place category", guidance: `Choose this if “${name}” describes what the venue is.`, venueType: true };
  if (tag.includes(":genre:place:")) return { label: "Venue style", guidance: `Choose this if “${name}” describes the venue's style.`, venueType: false };
  if (tag.includes(":setting:qloo:")) return { label: "Setting", guidance: `Choose this if “${name}” describes the atmosphere.`, venueType: false };
  if (tag.includes(":activity_type:qloo:")) return { label: "Activity", guidance: `Choose this if “${name}” describes what guests do.`, venueType: false };
  if (tag.includes(":amenity:qloo:")) return { label: "Amenity", guidance: `Choose this if “${name}” is a feature the venue offers.`, venueType: false };
  if (tag.includes(":dining_option:qloo:")) return { label: "Dining option", guidance: `Choose this if “${name}” describes a dining service.`, venueType: false };
  if (tag.includes(":product_service:qloo:")) return { label: "Product or service", guidance: `Choose this if “${name}” describes what the business sells.`, venueType: false };
  if (tag.includes(":cuisine:qloo:")) return { label: "Food or drink style", guidance: `Choose this only if “${name}” is the intended food or drink signal.`, venueType: false };
  if (tag.includes(":target_audience:qloo:")) return { label: "Audience", guidance: `Choose this if “${name}” describes the guests rather than the venue.`, venueType: false };
  if (tag.includes(":industry:qloo:")) return { label: "Industry", guidance: "Choose this for broad business-sector context.", venueType: false };
  if (tag.includes(":good_for:qloo:")) return { label: "Occasion", guidance: `Choose this if “${name}” describes an occasion.`, venueType: false };
  if (tag.includes(":keyword:")) return { label: "Listing keyword", guidance: "Choose this for a narrower listing description.", venueType: false };
  if (tag.includes(":genre:music:")) return { label: "Music genre", guidance: "Choose this if the music style is the core concept.", venueType: false };
  return { label: "Other Qloo tag", guidance: "Choose this only if it matches the venue concept you intended.", venueType: false };
}

export default function DecisionPage() {
  const [form, setForm] = useState<Form>(initial);
  const [extraVenues, setExtraVenues] = useState<{
    name: string; region: string; live_music_allowed: boolean; budget_limit: string;
  }[]>([]);
  const [artistShortlist, setArtistShortlist] = useState("");
  const [decision, setDecision] = useState<Decision | null>(null);
  const [busy, setBusy] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStage, setJobStage] = useState("");
  const [reviewBusy, setReviewBusy] = useState(false);
  const [reviewJobId, setReviewJobId] = useState<string | null>(null);
  const [reviewStage, setReviewStage] = useState("");
  const [reviewAlternate, setReviewAlternate] = useState({ audience: "", region: "" });
  const activeJob = useRef<string | null>(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<SavedDecision[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [pendingOption, setPendingOption] = useState<string | null>(null);
  const [scenarioInput, setScenarioInput] = useState<{
    venue_id: string; audience: string | null; region: string | null;
  }>({ venue_id: "", audience: null, region: null });
  const [pilot, setPilot] = useState<PilotPlan>({
    venue_id: "", owner: "", target_date: "", success_measure: "", baseline: "",
    cost_assumption: "", next_action: "Confirm artist availability and fee",
  });
  const [quotedCost, setQuotedCost] = useState("");
  const [outcome, setOutcome] = useState({
    metric: "Attendance", baseline_value: "", actual_value: "",
    unit: "people", period: "One pilot event", source: "", notes: "",
  });
  const isSample = decision?.source_mode === "sample";

  function showSample() {
    setDecision(sampleDecision);
    setPendingOption(null);
    setHistoryOpen(false);
    setError("");
    setJobStage("");
    requestAnimationFrame(() => document.getElementById("decision-options")?.scrollIntoView({ behavior: "smooth" }));
  }

  function closeSample() {
    setDecision(null);
    setError("");
    requestAnimationFrame(() => document.getElementById("decision-brief")?.scrollIntoView({ behavior: "smooth" }));
  }

  async function importVenues(file?: File) {
    if (!file) return;
    setError("");
    try {
      if (file.size > 100_000) throw new Error("Venue CSV must be under 100 KB");
      const venues = parseVenueCsv(await file.text());
      const [first, ...rest] = venues;
      setForm((current) => ({ ...current, venue_name: first.name, region: first.region,
        live_music_allowed: first.live_music_allowed, budget_limit: first.budget_limit }));
      setExtraVenues(rest);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  }

  async function loadHistory() {
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/decisions`);
      if (!response.ok) throw new Error(`Could not load decisions (${response.status})`);
      setHistory(await response.json() as SavedDecision[]);
      setHistoryOpen(true);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  }

  async function openDecision(id: string) {
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/decisions/${id}`);
      if (!response.ok) throw new Error(`Could not open decision (${response.status})`);
      setDecision(await response.json() as Decision);
      setHistoryOpen(false);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  }

  async function create(selectedTagId?: string) {
    setBusy(true); setError(""); setJobStage("Starting decision…");
    let startedJobId: string | null = null;
    try {
      const resolving = Boolean(selectedTagId && decision);
      const response = await fetch(resolving
        ? `${API_BASE}/api/decisions/${decision?.id}/resolve-jobs`
        : `${API_BASE}/api/decision-jobs`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(resolving ? { candidate_id: selectedTagId } : {
          ...form,
          artist_shortlist: artistShortlist.split("\n").map((name) => name.trim()).filter(Boolean),
          budget_limit: form.budget_limit === "" ? null : Number(form.budget_limit),
          venues: [
            { name: form.venue_name, region: form.region,
              live_music_allowed: form.live_music_allowed,
              budget_limit: form.budget_limit === "" ? null : Number(form.budget_limit) },
            ...extraVenues.map((venue) => ({ ...venue,
              budget_limit: venue.budget_limit === "" ? null : Number(venue.budget_limit) })),
          ],
        }),
      });
      if (!response.ok) throw new Error(`Decision request failed (${response.status}): ${await response.text()}`);
      const started = await response.json() as { job_id: string };
      startedJobId = started.job_id;
      activeJob.current = started.job_id;
      setJobId(started.job_id);
      for (;;) {
        await new Promise((resolve) => setTimeout(resolve, 600));
        if (activeJob.current !== started.job_id) return;
        const poll = await fetch(`${API_BASE}/api/decision-jobs/${started.job_id}`);
        if (!poll.ok) throw new Error(`Could not check decision progress (${poll.status})`);
        const state = await poll.json() as {
          status: string; stage: string; elapsed_seconds: number;
          decision: Decision | null; error: string | null;
        };
        if (activeJob.current !== started.job_id) return;
        setJobStage(`${state.stage} · ${state.elapsed_seconds}s`);
        if (state.status === "done" && state.decision) {
          setDecision(state.decision);
          break;
        }
        if (state.status === "cancelled") break;
        if (state.status === "error") throw new Error(state.error || "Decision failed");
      }
    } catch (cause) {
      if (!startedJobId || activeJob.current === startedJobId)
        setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      if (!startedJobId || activeJob.current === startedJobId) {
        activeJob.current = null;
        setJobId(null);
        setBusy(false);
      }
    }
  }

  async function cancelCreate() {
    const id = activeJob.current;
    if (!id) return;
    setJobStage("Requesting cancellation…");
    try {
      const response = await fetch(`${API_BASE}/api/decision-jobs/${id}`, { method: "DELETE" });
      if (!response.ok) throw new Error(`Cancellation failed (${response.status})`);
      const state = await response.json() as { status: string; decision: Decision | null };
      activeJob.current = null;
      setJobId(null);
      if (state.status === "done" && state.decision) setDecision(state.decision);
      setJobStage(state.status === "done" ? "Complete" : "Cancellation requested");
      setBusy(false);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  }

  async function select(optionId: string) {
    if (!decision || isSample) return;
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_BASE}/api/decisions/${decision.id}/select/${optionId}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...pilot,
          quoted_total_cost: quotedCost === "" ? null : Number(quotedCost),
          venue_id: pilot.venue_id || (decision.venues.length === 1 ? decision.venues[0].id : "") }),
      });
      if (!response.ok) throw new Error(`Selection failed (${response.status}): ${await response.text()}`);
      setDecision(await response.json() as Decision);
      setPendingOption(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally { setBusy(false); }
  }

  async function recordOutcome() {
    if (!decision || isSample) return;
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_BASE}/api/decisions/${decision.id}/outcome`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...outcome,
          baseline_value: Number(outcome.baseline_value),
          actual_value: Number(outcome.actual_value),
        }),
      });
      if (!response.ok) throw new Error(`Outcome could not be recorded (${response.status}): ${await response.text()}`);
      setDecision(await response.json() as Decision);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setBusy(false); }
  }

  async function compareScenario() {
    if (!decision || isSample) return;
    const venue = decision.venues.find((item) => item.id === scenarioInput.venue_id)
      || decision.venues.find((item) => item.live_music_allowed);
    if (!venue) return;
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_BASE}/api/decisions/${decision.id}/scenarios`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ venue_id: venue.id,
          audience: scenarioInput.audience ?? decision.request?.audience ?? form.audience,
          region: scenarioInput.region ?? venue.region }),
      });
      if (!response.ok) throw new Error(`Scenario failed (${response.status}): ${await response.text()}`);
      const result = await response.json() as { decision: Decision };
      setDecision(result.decision);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setBusy(false); }
  }

  async function reviewPilot() {
    if (!decision || isSample || !decision.snapshot_fingerprint) return;
    if (reviewAlternate.audience.trim() && reviewAlternate.region.trim()) {
      setError("Choose either an alternate audience or an alternate region for the review.");
      return;
    }
    setReviewBusy(true); setError(""); setReviewStage("Starting review…");
    try {
      const alternate_audience = reviewAlternate.audience.trim() || null;
      const alternate_region = reviewAlternate.region.trim() || null;
      const venue = scenarioVenue ?? decision.venues.find((item) => item.live_music_allowed);
      const response = await fetch(`${API_BASE}/api/decisions/${decision.id}/agent-reviews`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ snapshot_fingerprint: decision.snapshot_fingerprint,
          scenario_venue_id: (alternate_audience || alternate_region) ? venue?.id : null,
          alternate_audience, alternate_region }),
      });
      if (!response.ok) throw new Error(`Review could not start (${response.status}): ${await response.text()}`);
      const started = await response.json() as { review_id: string };
      setReviewJobId(started.review_id);
      for (;;) {
        await new Promise((resolve) => setTimeout(resolve, 700));
        const poll = await fetch(`${API_BASE}/api/decisions/${decision.id}/agent-reviews/${started.review_id}`);
        if (!poll.ok) throw new Error(`Could not check review progress (${poll.status})`);
        const state = await poll.json() as { status: string; stage: string; error: string | null };
        setReviewStage(state.stage);
        if (state.status === "done") {
          const refreshed = await fetch(`${API_BASE}/api/decisions/${decision.id}`);
          if (!refreshed.ok) throw new Error("Review finished, but the decision could not be reopened.");
          setDecision(await refreshed.json() as Decision);
          break;
        }
        if (state.status === "cancelled") break;
        if (state.status === "error") throw new Error(state.error || "Review unavailable");
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setReviewBusy(false); setReviewJobId(null); }
  }

  async function cancelReview() {
    if (!decision || !reviewJobId) return;
    const response = await fetch(`${API_BASE}/api/decisions/${decision.id}/agent-reviews/${reviewJobId}`, { method: "DELETE" });
    if (!response.ok) setError(`Could not cancel review (${response.status})`);
    else setReviewStage("Cancellation requested");
  }

  async function replayDecision() {
    if (!decision || isSample) return;
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_BASE}/api/decisions/${decision.id}/replay`, {
        method: "POST",
      });
      if (!response.ok) throw new Error(`Replay failed (${response.status})`);
      setDecision(await response.json() as Decision);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setBusy(false); }
  }

  const fields: { key: keyof Form; label: string; placeholder: string }[] = [
    { key: "venue_name", label: "Venue", placeholder: "Your real venue name" },
    { key: "concept", label: "Venue concept", placeholder: "e.g. listening bar" },
    { key: "region", label: "Region", placeholder: "e.g. Williamsburg, Brooklyn" },
    { key: "audience", label: "Audience", placeholder: "e.g. young professionals" },
    { key: "objective", label: "Decision objective", placeholder: "What are you trying to choose?" },
    { key: "budget_limit", label: "Budget ceiling (optional)", placeholder: "Amount in your local currency" },
  ];
  const scenarioVenue = decision?.venues.find((venue) => venue.id === scenarioInput.venue_id)
    ?? decision?.venues.find((venue) => venue.live_music_allowed);
  const latestReview = decision?.agent_reviews?.at(-1);
  const reviewStale = Boolean(latestReview && latestReview.snapshot_fingerprint !== decision?.snapshot_fingerprint);

  return <div className="decision-shell">
    <header className="decision-topbar">
      <Link href="/" className="decision-brand" aria-label="Tastewell home"><span className="decision-brand-mark">t<span>.</span></span><span>tastewell</span></Link>
      <button onClick={() => void loadHistory()} className="decision-history-button">Saved decisions</button>
    </header>
    <div className="decision-layout">
    <aside className="decision-rail" aria-label="Decision guide">
      <div className="decision-rail-inner">
        <p className="decision-rail-label">Your decision trail</p>
        <h2>Better nights start with better questions.</h2>
        <p className="decision-rail-copy">Build a small, evidence-backed shortlist. Then choose a room, name the unknowns, and record what actually happened.</p>
        <ol className="decision-steps">
          <li className="is-active"><span>1</span><div><strong>Set the brief</strong><small>Rooms, audience &amp; limits</small></div></li>
          <li className={decision?.options.length ? "is-active" : ""}><span>2</span><div><strong>Explore options</strong><small>Ranks &amp; source evidence</small></div></li>
          <li className={decision?.selected_option_id ? "is-active" : ""}><span>3</span><div><strong>Plan the pilot</strong><small>Owner, timing &amp; measure</small></div></li>
          <li className={decision?.outcome ? "is-active" : ""}><span>4</span><div><strong>Record the outcome</strong><small>What your own data shows</small></div></li>
        </ol>
        <div className="decision-rail-note"><strong>What Qloo brings</strong><p>Aggregate cultural signals to compare a shortlist. Availability, costs, and results stay with your team.</p></div>
      </div>
    </aside>
    <main className="decision-main">
    <section className="decision-intro">
      <h1>Make the next night count.</h1>
      <p>Find an artist-led pilot that fits your audience and your venues. Keep the evidence and the operational questions together as you decide.</p>
      <div className="decision-scope"><span className="decision-scope-dot" />Currently exploring <strong>live music</strong> <span aria-hidden="true">·</span> Up to 10 venues</div>
      <div className="decision-example-action">
        <button type="button" onClick={isSample ? closeSample : showSample}>
          {isSample ? "Start your own decision" : "See an illustrative decision"}
        </button>
        <span>{isSample ? "The example uses invented names and IDs; no Qloo call was made." : "Opens instantly with a sample pilot and rank-changing scenario."}</span>
      </div>
    </section>
    {historyOpen && <section className="decision-history mb-5 rounded-xl border border-zinc-700 bg-zinc-900 p-4">
      <h2 className="font-semibold">Recent decisions</h2>
      {history.length === 0 && <p className="mt-2 text-sm text-zinc-400">No decisions saved yet.</p>}
      <div className="mt-3 grid gap-2">{history.map((item) =>
        <button key={item.id} onClick={() => void openDecision(item.id)}
          className="rounded-md border border-zinc-700 p-3 text-left text-sm hover:border-amber-400">
          {item.venue_name} · {item.concept} · {item.region}
          <span className="block text-xs text-zinc-500">{item.source_mode === "replay" ? "Replay · " : ""}{item.has_outcome ? "Outcome recorded" : item.selected_option_id ? "Pilot selected" : item.status} · {item.updated_at}</span>
        </button>)}</div></section>}
    {!isSample && <form id="decision-brief" onSubmit={(event) => { event.preventDefault(); void create(); }} className="decision-form rounded-xl border border-zinc-700 bg-zinc-900 p-5">
      <div className="decision-form-heading"><div><h2>Shape your pilot brief</h2><p>Start with the venue and the people you want to reach.</p></div><span>01 / Brief</span></div>
      <div className="grid gap-4 sm:grid-cols-2">{fields.map(({ key, label, placeholder }) =>
        <label key={key} className="text-sm text-zinc-300">{label}
          <input required={key !== "budget_limit"} type={key === "budget_limit" ? "number" : "text"}
            min={key === "budget_limit" ? 0 : undefined} placeholder={placeholder}
            value={String(form[key])} onChange={(event) => setForm({ ...form, [key]: event.target.value })}
            className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2 text-zinc-100" />
        </label>)}</div>
      <label className="mt-4 flex items-center gap-2 text-sm"><input type="checkbox" checked={form.live_music_allowed}
        onChange={(event) => setForm({ ...form, live_music_allowed: event.target.checked })} />Live music is permitted at this venue</label>
      <div className="decision-venues mt-5 border-t border-zinc-700 pt-4">
        <div className="flex items-center justify-between gap-3"><h2 className="font-medium">Additional venues</h2>
          <button type="button" disabled={extraVenues.length >= 9} onClick={() => setExtraVenues([...extraVenues,
            { name: "", region: "", live_music_allowed: true, budget_limit: "" }])}
            className="rounded-md border border-zinc-600 px-3 py-1 text-sm disabled:opacity-50">Add venue</button></div>
        <label className="mt-3 block text-xs text-zinc-400">Import venue CSV (replaces the venue fields above; 1–10 rows)
          <input type="file" accept=".csv,text/csv" onChange={(event) => { void importVenues(event.target.files?.[0]); event.target.value = ""; }}
            className="mt-1 block w-full text-sm" />
        </label>
        <p className="text-xs text-zinc-500">Columns: name,region,live_music_allowed,budget_limit. Use true/false; leave budget blank when unknown.</p>
        {extraVenues.map((venue, index) => <div key={index} className="mt-3 grid gap-3 rounded-lg border border-zinc-700 p-3 sm:grid-cols-2">
          <label className="text-sm">Venue name<input required value={venue.name}
            onChange={(event) => setExtraVenues(extraVenues.map((item, i) => i === index ? { ...item, name: event.target.value } : item))}
            className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" /></label>
          <label className="text-sm">Region<input required value={venue.region}
            onChange={(event) => setExtraVenues(extraVenues.map((item, i) => i === index ? { ...item, region: event.target.value } : item))}
            className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" /></label>
          <label className="text-sm">Budget ceiling (optional)<input type="number" min="0" value={venue.budget_limit}
            onChange={(event) => setExtraVenues(extraVenues.map((item, i) => i === index ? { ...item, budget_limit: event.target.value } : item))}
            className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" /></label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={venue.live_music_allowed}
            onChange={(event) => setExtraVenues(extraVenues.map((item, i) => i === index ? { ...item, live_music_allowed: event.target.checked } : item))} />Live music permitted</label>
          <button type="button" onClick={() => setExtraVenues(extraVenues.filter((_, i) => i !== index))}
            className="text-left text-xs text-zinc-400 underline">Remove venue</button>
        </div>)}
      </div>
      <label className="decision-shortlist mt-5 block text-sm text-zinc-300">Your artist shortlist (optional; one name per line, up to five)
        <textarea rows={3} value={artistShortlist} onChange={(event) => setArtistShortlist(event.target.value)}
          placeholder={"Miles Davis\nAnother act you are considering"}
          className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2 text-zinc-100" />
      </label>
      <button disabled={busy} className="decision-primary mt-5 rounded-md bg-amber-400 px-4 py-2 font-semibold text-zinc-950 disabled:opacity-50">{busy ? "Checking Qloo…" : "Explore options"}</button>
      {jobId && <button type="button" onClick={() => void cancelCreate()}
        className="ml-3 rounded-md border border-zinc-600 px-4 py-2 text-sm">Cancel decision</button>}
      {jobStage && <p role="status" className="mt-2 text-xs text-zinc-400">{jobStage}</p>}
    </form>}
    {error && <p role="alert" className="mt-5 rounded-md border border-red-700 p-3 text-red-300">{error}</p>}
    {decision && <section id="decision-options" className="decision-results mt-8" aria-live="polite">
      <h2 className="text-xl font-semibold">{decision.status === "ready" ? "Pilot options" : "Decision needs attention"}</h2>
      <p className="mt-1 text-xs text-zinc-500">{isSample
        ? "Illustrative example · invented names, IDs and ranks · no Qloo call · not saved"
        : `Decision ${decision.id} · ${decision.source_mode === "replay" ? `Replay of ${decision.replay_of}; no new Qloo call` : "Current decision"} · Saved on this server.`}</p>
      {isSample && <div className="decision-sample-notice" role="note">
        <strong>Sample brief</strong> · Two fictional Austin venues are choosing an artist-led Thursday pilot for local indie and soul listeners. Every source row below is illustrative; run your own decision for live Qloo evidence.
      </div>}
      {!isSample && <div className="mt-3 flex flex-wrap gap-3 text-xs">
        <button disabled={busy} onClick={() => void replayDecision()}
          className="rounded-md border border-zinc-600 px-3 py-2">Replay saved evidence</button>
        <a href={`${API_BASE}/api/decisions/${decision.id}/export`}
          className="rounded-md border border-zinc-600 px-3 py-2">Export decision JSON</a>
      </div>}
      {decision.notes.map((note, i) => <p key={i} className="mt-2 text-sm text-zinc-300">{note}</p>)}
      {decision.status === "needs_input" && <div className="decision-choice-panel mt-4 rounded-lg border border-amber-700 p-4">
        <h3 className="font-medium">{decision.resolution_kind === "artist"
          ? `Choose the intended artist for ${decision.resolution_key}`
          : "Choose the intended concept tag"}</h3>
        <p className="decision-choice-help">{decision.resolution_kind === "artist"
          ? "Qloo found more than one artist record. Confirm the intended act; if names are identical, the record IDs are the only distinction currently available."
          : "These matches represent different things. Pick the one that describes your venue concept; that tag will guide the artist and brand search."}</p>
        <div className="decision-choice-grid">{decision.candidates.map((candidate) => {
          const display = describeTagChoice(candidate.id, candidate.name || "this match");
          return <button key={candidate.id} disabled={busy} onClick={() => void create(candidate.id)}
            className={`decision-choice ${decision.resolution_kind === "tag" && display.venueType ? "is-venue-type" : ""}`}>
            <span className="decision-choice-name">{candidate.name || "Unnamed Qloo match"}</span>
            {decision.resolution_kind === "tag" ? <>
              <span className="decision-choice-kind">{display.label}{display.venueType ? " · venue-type match" : ""}</span>
              <span className="decision-choice-guidance">{display.guidance}</span>
            </> : <>
              <span className="decision-choice-kind">Artist record</span>
              <span className="decision-choice-guidance">Record ID: {candidate.id}</span>
            </>}
          </button>;
        })}</div>
      </div>}
      <div className="decision-options-grid mt-5 grid gap-4 md:grid-cols-3">{decision.options.map((option, index) =>
        <article key={option.id} className="decision-option rounded-xl border border-zinc-700 bg-zinc-900 p-4">
          <div className="decision-option-top"><span>Option {String(index + 1).padStart(2, "0")}</span><span>{option.evidence_ids.length} sources</span></div>
          <h3 className="font-semibold">{option.title}</h3><p className="mt-2 text-sm">{option.description}</p>
          {option.artist_rank && <p className="mt-2 text-xs text-amber-300">Artist #{option.artist_rank} within this {isSample ? "illustrative" : "Qloo"} shortlist</p>}
          {decision.venues.length > 1 && <div className="mt-3 border-t border-zinc-700 pt-3 text-xs">
            <p className="font-medium text-zinc-300">Venue comparison · rank within each separate call</p>
            {decision.venues.map((venue) => <p key={venue.id} className="mt-1 text-zinc-400">
              {venue.name}: {!venue.live_music_allowed ? "Excluded · no live music" : option.venue_ranks[venue.id] ? `artist #${option.venue_ranks[venue.id]}` : "rank unavailable"}
            </p>)}
          </div>}
          <p className="mt-4 text-xs uppercase tracking-wide text-zinc-500">What is unknown</p>
          <ul className="mt-1 list-inside list-disc text-sm text-zinc-300">{option.unknowns.map((item) => <li key={item}>{item}</li>)}</ul>
          <p className="mt-3 text-xs text-zinc-400">{option.constraint_notes.join(" ")}</p>
          <details className="mt-4 text-xs"><summary className="cursor-pointer text-amber-300">Inspect {isSample ? "illustrative source rows" : "Qloo evidence"}</summary>
            {option.evidence_ids.map((id) => { const row = decision.evidence.find((e) => e.id === id);
              return row && <div id={`evidence-${id}`} key={id} className="mt-2 break-words border-t border-zinc-700 pt-2">
                <strong>{row.name || row.source_id}</strong> · {row.operation} · {row.status}
                <div>ID: {row.source_id}</div><div>Affinity: {row.affinity ?? "not provided"}</div>
                <div>Query: {JSON.stringify(row.query)}</div><div>Correlation: {row.correlation_id || "not provided"}</div>
                <div>Retrieved: {row.retrieved_at}</div></div>; })}</details>
          {isSample ? decision.selected_option_id === option.id && <span className="decision-sample-selection">Sample pilot selected</span> : <button onClick={() => setPendingOption(option.id)} disabled={busy}
            className="mt-4 rounded-md border border-amber-400 px-3 py-2 text-sm text-amber-300 disabled:opacity-50">
            {decision.selected_option_id === option.id ? "Selected · edit plan" : "Plan this pilot"}</button>}
        </article>)}</div>
      {decision.status === "ready" && !isSample && <section className="decision-agent-review" aria-labelledby="agent-review-title">
        <div className="decision-agent-heading">
          <div><h3 id="agent-review-title">Review the pilot choice</h3>
            <p>A bounded agent inspects this saved Qloo shortlist and venue facts. It can propose a pilot, ask for a missing fact, or abstain. You decide whether to record a selection.</p></div>
          <span>{decision.source_mode === "replay" ? "Saved evidence replay" : "Live Qloo decision"}</span>
        </div>
        {decision.source_mode === "live" && <div className="decision-review-context">
          <p>Optional: test one context change during the review. Leave both blank to review the current evidence.</p>
          <label>Venue
            <select value={scenarioVenue?.id || ""} onChange={(event) => setScenarioInput({ ...scenarioInput, venue_id: event.target.value })}>
              {decision.venues.filter((venue) => venue.live_music_allowed).map((venue) => <option key={venue.id} value={venue.id}>{venue.name}</option>)}
            </select>
          </label>
          <label>Alternate audience
            <input value={reviewAlternate.audience} onChange={(event) => setReviewAlternate({ audience: event.target.value, region: "" })} placeholder="Optional audience wording" />
          </label>
          <label>Alternate region
            <input value={reviewAlternate.region} onChange={(event) => setReviewAlternate({ audience: "", region: event.target.value })} placeholder="Optional region" />
          </label>
        </div>}
        <div className="decision-review-actions">
          <button type="button" className="decision-primary" disabled={busy || reviewBusy} onClick={() => void reviewPilot()}>{reviewBusy ? "Reviewing…" : "Review the pilot choice"}</button>
          {reviewBusy && <button type="button" onClick={() => void cancelReview()}>Cancel review</button>}
          {reviewBusy && <span role="status">{reviewStage}</span>}
        </div>
        {latestReview && <div className="decision-review-result" aria-live="polite">
          <p className="decision-review-status">{reviewStale ? "Earlier review · evidence has changed" : latestReview.status === "recommend" ? "Agent proposal · operator approval needed" : latestReview.status === "needs_input" ? "Agent needs input" : "Agent abstained"}</p>
          {latestReview.status === "recommend" ? <>
            <h4>{decision.options.find((option) => option.id === latestReview.option_id)?.title} at {decision.venues.find((venue) => venue.id === latestReview.venue_id)?.name}</h4>
            <p>{latestReview.rationale}</p>
            <p className="decision-review-interpretation">Agent interpretation. Qloo sources and operator facts are listed below; booking and cost remain unverified.</p>
            <div className="decision-review-facts"><strong>Qloo sources used</strong>
              {latestReview.evidence_ids.map((id) => { const row = decision.evidence.find((item) => item.id === id);
                return row && <a key={id} href={`#evidence-${id}`} onClick={() => {
                  document.getElementById(`evidence-${id}`)?.closest("details")?.setAttribute("open", "");
                }}>{row.name || row.source_id || id} · {row.operation} · {row.status}</a>; })}
            </div>
            {latestReview.scenario_id && <p>Requested a fixed-shortlist comparison. <a href={`#scenario-${latestReview.scenario_id}`}>Inspect rank movement</a>.</p>}
            {latestReview.alternatives.length > 0 && <p>Alternatives considered: {latestReview.alternatives.map((id) => decision.options.find((item) => item.id === id)?.title || id).join(", ")}.</p>}
            <p><strong>Still unknown:</strong> {latestReview.unknowns.join("; ")}.</p>
            <p><strong>Next check:</strong> {latestReview.next_check}</p>
            {!reviewStale && <button type="button" className="decision-primary" onClick={() => {
              setPendingOption(latestReview.option_id); setPilot((current) => ({ ...current, venue_id: latestReview.venue_id || "" }));
              requestAnimationFrame(() => document.getElementById("pilot-plan")?.scrollIntoView({ behavior: "smooth" }));
            }}>Choose this pilot</button>}
          </> : <p>{latestReview.reason}</p>}
          <details><summary>What the agent checked</summary><ul>{latestReview.actions.map((action, index) => <li key={`${action.tool}-${index}`}>
            {action.tool === "inspect_option" ? "Inspected an option and its saved Qloo rows" : action.tool === "check_venue" ? "Checked operator venue constraints" : "Requested a changed-context Qloo rank"} · {action.outcome}
            <details><summary>Tool arguments and source IDs</summary><pre>{JSON.stringify({ arguments: action.arguments, evidence_ids: action.evidence_ids, scenario_id: action.scenario_id }, null, 2)}</pre></details>
          </li>)}</ul></details>
        </div>}
      </section>}
      {decision.status === "ready" && decision.options.some((option) => option.artist_rank) &&
        <section className="decision-scenario mt-6 rounded-xl border border-zinc-700 bg-zinc-900 p-5">
          <h3 className="font-semibold">Scenario comparison</h3>
          <p className="mt-1 text-sm text-zinc-400">{isSample
            ? "This invented example holds the artist IDs fixed and changes the audience. A live comparison makes a separate Qloo call."
            : "Keep the artist IDs fixed and change one audience or region. Each rank is within its own Qloo call."}</p>
          {!isSample && <form onSubmit={(event) => { event.preventDefault(); void compareScenario(); }}
            className="mt-4 grid gap-3 sm:grid-cols-3">
            <label className="text-sm">Venue
              <select value={scenarioVenue?.id || ""}
                onChange={(event) => { const venue = decision.venues.find((item) => item.id === event.target.value);
                  setScenarioInput({ ...scenarioInput, venue_id: event.target.value, region: venue?.region ?? null }); }}
                className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2">
                {decision.venues.filter((venue) => venue.live_music_allowed).map((venue) =>
                  <option key={venue.id} value={venue.id}>{venue.name}</option>)}
              </select>
            </label>
            <label className="text-sm">Scenario audience
              <input required value={scenarioInput.audience ?? decision.request?.audience ?? form.audience}
                onChange={(event) => setScenarioInput({ ...scenarioInput, audience: event.target.value })}
                className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" />
            </label>
            <label className="text-sm">Scenario region
              <input required value={scenarioInput.region ?? scenarioVenue?.region ?? ""}
                onChange={(event) => setScenarioInput({ ...scenarioInput, region: event.target.value })}
                className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" />
            </label>
            <button disabled={busy} className="rounded-md bg-amber-400 px-4 py-2 font-semibold text-zinc-950 disabled:opacity-50">Compare scenario</button>
          </form>}
          {(decision.scenarios || []).slice().reverse().map((scenario) =>
            <div id={`scenario-${scenario.id}`} key={scenario.id} className="mt-5 border-t border-zinc-700 pt-4 text-sm">
              <p className="font-medium">{decision.venues.find((venue) => venue.id === scenario.venue_id)?.name} · {scenario.status === "ready" ? "Ranked" : "Rank unavailable"}</p>
              <p className="mt-1 text-zinc-400">{scenario.note}</p>
              <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-xs">
                <thead><tr><th className="pb-2">Artist</th><th>Original rank</th><th>Scenario rank</th><th>Change</th></tr></thead>
                <tbody>{scenario.artist_ids.map((id) => { const before = scenario.baseline_ranks[id]; const after = scenario.scenario_ranks[id];
                  return <tr key={id} className="border-t border-zinc-700">
                    <td className="py-2">{scenario.artist_names[id] || id}</td>
                    <td>{before ?? "unavailable"}</td><td>{after ?? "unavailable"}</td>
                    <td>{before && after ? before === after ? "unchanged" : after < before ? `up ${before - after}` : `down ${after - before}` : "unknown"}</td>
                  </tr>; })}</tbody>
              </table></div>
              <details className="mt-3 text-xs"><summary className="cursor-pointer text-amber-300">Inspect scenario queries and evidence</summary>
                <p className="mt-2 break-words">Original: {JSON.stringify(scenario.original_query)}</p>
                <p className="mt-1 break-words">Changed: {JSON.stringify(scenario.changed_query)}</p>
                {scenario.evidence_ids.map((id) => { const row = decision.evidence.find((item) => item.id === id);
                  return row && <p key={id} className="mt-1 break-words">{row.name || row.source_id || "No entity"} · {row.status} · {row.source_id || "No ID"} · {row.correlation_id || "No correlation"}</p>; })}
              </details>
            </div>)}
        </section>}
      {pendingOption && !isSample && <form id="pilot-plan" onSubmit={(event) => { event.preventDefault(); void select(pendingOption); }}
        className="decision-plan mt-6 rounded-xl border border-amber-700 bg-zinc-900 p-5">
        <h3 className="text-lg font-semibold">Record the pilot</h3>
        <p className="mt-1 text-sm text-zinc-400">Use your own operational facts. Qloo does not provide booking, cost, or outcome data.</p>
        <label className="mt-4 block text-sm">Pilot venue
          <select required value={pilot.venue_id || (decision.venues.length === 1 ? decision.venues[0].id : "")}
            onChange={(event) => setPilot({ ...pilot, venue_id: event.target.value })}
            className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2">
            <option value="">Choose a venue</option>
            {decision.venues.filter((venue) => venue.live_music_allowed).map((venue) =>
              <option key={venue.id} value={venue.id}>{venue.name} · {venue.region}</option>)}
          </select>
        </label>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">{([
          ["owner", "Owner"], ["target_date", "Target date or window"],
          ["success_measure", "Success measure"], ["baseline", "Baseline source or value"],
          ["cost_assumption", "Cost assumption"], ["next_action", "Next action"],
        ] as [keyof PilotPlan, string][]).map(([key, label]) =>
          <label key={key} className="text-sm">{label}
            <input required={key === "owner" || key === "target_date" || key === "success_measure" || key === "next_action"}
              value={pilot[key]} onChange={(event) => setPilot({ ...pilot, [key]: event.target.value })}
              className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" />
          </label>)}</div>
        <label className="mt-3 block text-sm">Known total pilot cost (optional; same currency as venue budget)
          <input type="number" min="0" step="1" value={quotedCost}
            onChange={(event) => setQuotedCost(event.target.value)}
            className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" />
        </label>
        <p className="mt-1 text-xs text-zinc-500">When supplied, this amount must not exceed the selected venue&apos;s budget ceiling. Unknown cost remains unverified.</p>
        <button disabled={busy} className="mt-4 rounded-md bg-amber-400 px-4 py-2 font-semibold text-zinc-950">Record selection</button>
      </form>}
      {decision.selected_option_id && <p className="mt-5 rounded-md border border-green-700 p-3 text-sm text-green-300">
        {isSample ? "Illustrative pilot plan" : "Selection recorded"} for {decision.venues.find((venue) => venue.id === decision.pilot_plan?.venue_id)?.name} on {decision.pilot_plan?.target_date}. Owner: {decision.pilot_plan?.owner}. Next: {decision.pilot_plan?.next_action}.</p>}
      {isSample && decision.pilot_plan && <p className="decision-sample-plan">Success measure: {decision.pilot_plan.success_measure}. Baseline: {decision.pilot_plan.baseline}. Cost assumption: {decision.pilot_plan.cost_assumption}. No event or outcome has occurred in this example.</p>}
      {decision.selected_option_id && !isSample && <div className="decision-outcome mt-5 rounded-xl border border-zinc-700 bg-zinc-900 p-5">
        <h3 className="font-semibold">Pilot outcome</h3>
        <p className="mt-1 text-sm text-zinc-400">Enter aggregated results from your own records. A difference from baseline does not establish that this program caused it.</p>
        {decision.outcome && <p className="mt-3 text-sm text-green-300">Recorded: {decision.outcome.metric} {decision.outcome.baseline_value} → {decision.outcome.actual_value} {decision.outcome.unit} ({decision.outcome.period}). Source: {decision.outcome.source}.</p>}
        <form onSubmit={(event) => { event.preventDefault(); void recordOutcome(); }} className="mt-4 grid gap-3 sm:grid-cols-2">
          {([
            ["metric", "Metric"], ["baseline_value", "Baseline value"],
            ["actual_value", "Actual value"], ["unit", "Unit"],
            ["period", "Measurement period"], ["source", "Operator data source"],
            ["notes", "Notes (optional)"],
          ] as [keyof typeof outcome, string][]).map(([key, label]) =>
            <label key={key} className="text-sm">{label}
              <input required={key !== "notes"} type={key.endsWith("_value") ? "number" : "text"}
                value={outcome[key]} onChange={(event) => setOutcome({ ...outcome, [key]: event.target.value })}
                className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" />
            </label>)}
          <button disabled={busy} className="rounded-md bg-amber-400 px-4 py-2 font-semibold text-zinc-950 disabled:opacity-50">Record outcome</button>
        </form>
      </div>}
    </section>}
    <footer className="decision-footer mt-10 text-xs text-zinc-500">Qloo reports aggregate cultural affinity. It does not predict attendance, sales, or individual behavior.</footer>
    </main>
    </div>
  </div>;
}
