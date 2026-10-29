import type { Decision } from "./page";

const artistA = "urn:sample:artist:a";
const artistB = "urn:sample:artist:b";
const artistC = "urn:sample:artist:c";
const conceptTag = "urn:sample:tag:cocktail_bar";

// This fixture contains invented names, IDs and ranks. It never represents a Qloo response.
export const sampleDecision: Decision = {
  id: "illustrative-example",
  status: "ready",
  source_mode: "sample",
  replay_of: null,
  candidates: [],
  request: { audience: "Local indie and soul listeners" },
  venues: [
    { id: "sample-room", name: "Juniper Room (sample)", region: "Austin (sample)", live_music_allowed: true, budget_limit: 2500 },
    { id: "sample-annex", name: "Canal Annex (sample)", region: "Austin (sample)", live_music_allowed: true, budget_limit: 1800 },
  ],
  notes: [
    "Illustrative source rows below show how the real decision would be explained. All names, IDs and ranks in this example are invented.",
    "Costs and artist availability are unknown; the budget ceilings are operator assumptions, not Qloo results.",
  ],
  evidence: [
    { id: "sample-tag", operation: "find_tags", status: "sample", source_id: conceptTag, name: "Cocktail bar (illustrative)", affinity: null,
      query: { query: "cocktail bar", semantic: true }, correlation_id: "sample-1", retrieved_at: "illustrative only", summary: "Invented concept match" },
    { id: "sample-artist-a", operation: "recommend", status: "sample", source_id: artistA, name: "Sample Artist A", affinity: null,
      query: { target_type: "artist", signal_tags: [conceptTag], signal_location: "Austin (sample)", demographic: "Local indie and soul listeners" },
      correlation_id: "sample-2", retrieved_at: "illustrative only", summary: "Invented artist candidate" },
    { id: "sample-artist-b", operation: "recommend", status: "sample", source_id: artistB, name: "Sample Artist B", affinity: null,
      query: { target_type: "artist", signal_tags: [conceptTag], signal_location: "Austin (sample)", demographic: "Local indie and soul listeners" },
      correlation_id: "sample-2", retrieved_at: "illustrative only", summary: "Invented artist candidate" },
    { id: "sample-artist-c", operation: "recommend", status: "sample", source_id: artistC, name: "Sample Artist C", affinity: null,
      query: { target_type: "artist", signal_tags: [conceptTag], signal_location: "Austin (sample)", demographic: "Local indie and soul listeners" },
      correlation_id: "sample-2", retrieved_at: "illustrative only", summary: "Invented artist candidate" },
    ...([artistA, artistB, artistC] as const).map((id, index) => ({
      id: `sample-rank-${index + 1}`, operation: "rank", status: "sample", source_id: id,
      name: `Sample Artist ${String.fromCharCode(65 + index)}`, affinity: null,
      query: { options: [artistA, artistB, artistC], option_type: "artist", signal_location: "Austin (sample)", demographic: "Local indie and soul listeners" },
      correlation_id: "sample-3", retrieved_at: "illustrative only", summary: "Invented within-call rank",
    })),
    { id: "sample-partner", operation: "recommend", status: "sample", source_id: "urn:sample:brand:partner", name: "Sample Partner", affinity: null,
      query: { target_type: "brand", signal_tags: [conceptTag], signal_location: "Austin (sample)" },
      correlation_id: "sample-4", retrieved_at: "illustrative only", summary: "Invented partner candidate" },
  ],
  options: [
    { id: "sample-early", title: "Early live set", description: "Trial an early set with Sample Artist A at Juniper Room.", format: "early_set",
      evidence_ids: ["sample-tag", "sample-artist-a", "sample-rank-1"], artist_rank: 1,
      venue_ranks: { "sample-room": 1, "sample-annex": 2 },
      unknowns: ["Artist availability and fee", "Staffing and licensing", "Expected attendance and revenue"],
      constraint_notes: ["Live music permitted in the sample brief.", "Affordability remains unverified until costs are known."] },
    { id: "sample-listening", title: "Hosted listening session", description: "Trial a listening session featuring Sample Artist B at Canal Annex.", format: "listening_session",
      evidence_ids: ["sample-tag", "sample-artist-b", "sample-rank-2"], artist_rank: 2,
      venue_ranks: { "sample-room": 2, "sample-annex": 1 },
      unknowns: ["Artist availability and fee", "Staffing and licensing", "Expected attendance and revenue"],
      constraint_notes: ["Live music permitted in the sample brief.", "Affordability remains unverified until costs are known."] },
    { id: "sample-showcase", title: "Partner showcase", description: "Trial a showcase with Sample Artist C and explore Sample Partner at Juniper Room.", format: "partner_showcase",
      evidence_ids: ["sample-tag", "sample-artist-c", "sample-rank-3", "sample-partner"], artist_rank: 3,
      venue_ranks: { "sample-room": 3, "sample-annex": 3 },
      unknowns: ["Artist availability and fee", "Staffing and licensing", "Brand willingness to partner"],
      constraint_notes: ["Live music permitted in the sample brief.", "Partner fit and costs require operator verification."] },
  ],
  scenarios: [{
    id: "sample-scenario", venue_id: "sample-room", status: "ready", created_at: "illustrative only",
    original_query: { options: [artistA, artistB, artistC], demographic: "Local indie and soul listeners", signal_location: "Austin (sample)" },
    changed_query: { options: [artistA, artistB, artistC], demographic: "Local jazz and R&B listeners", signal_location: "Austin (sample)" },
    artist_ids: [artistA, artistB, artistC],
    artist_names: { [artistA]: "Sample Artist A", [artistB]: "Sample Artist B", [artistC]: "Sample Artist C" },
    baseline_ranks: { [artistA]: 1, [artistB]: 2, [artistC]: 3 },
    scenario_ranks: { [artistA]: 2, [artistB]: 1, [artistC]: 3 },
    evidence_ids: [],
    note: "Illustrative rank change over the same invented artist IDs. A live scenario would make a separate Qloo rank call.",
  }],
  selected_option_id: "sample-early",
  selected_at: "illustrative only",
  pilot_plan: {
    venue_id: "sample-room", owner: "Example operator", target_date: "One Thursday (illustrative)",
    success_measure: "Compare attendance with similar Thursdays", baseline: "Operator's prior Thursday records",
    cost_assumption: "Artist fee and staffing quotes pending", next_action: "Request artist fee and confirm staffing and licensing",
  },
  outcome: null,
  resolution_kind: null,
  resolution_key: null,
};
