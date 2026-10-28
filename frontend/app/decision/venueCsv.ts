export type ImportedVenue = {
  name: string;
  region: string;
  live_music_allowed: boolean;
  budget_limit: string;
};

// Small, strict CSV reader for a venue roster. Quoted commas and newlines are
// supported; malformed rows fail as a whole so the UI never imports half a list.
function cells(source: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < source.length; i += 1) {
    const char = source[i];
    if (char === '"') {
      if (quoted && source[i + 1] === '"') { cell += '"'; i += 1; }
      else if (quoted) quoted = false;
      else if (cell === "") quoted = true;
      else throw new Error("Invalid quote in venue CSV");
    } else if (quoted) cell += char;
    else if (char === ",") { row.push(cell); cell = ""; }
    else if (char === "\n") { row.push(cell); rows.push(row); row = []; cell = ""; }
    else if (char !== "\r") cell += char;
  }
  if (quoted) throw new Error("Unclosed quote in venue CSV");
  if (cell !== "" || row.length) { row.push(cell); rows.push(row); }
  return rows.filter((item) => item.some((value) => value.trim() !== ""));
}

export function parseVenueCsv(source: string): ImportedVenue[] {
  const rows = cells(source.replace(/^\uFEFF/, ""));
  const header = rows.shift()?.map((value) => value.trim().toLowerCase());
  const expected = ["name", "region", "live_music_allowed", "budget_limit"];
  if (!header || header.length !== expected.length ||
      expected.some((name, index) => header[index] !== name)) {
    throw new Error(`Venue CSV header must be: ${expected.join(",")}`);
  }
  if (!rows.length || rows.length > 10) throw new Error("Venue CSV needs 1–10 venues");
  const names = new Set<string>();
  return rows.map((row, index) => {
    if (row.length !== 4) throw new Error(`Venue CSV row ${index + 2} needs four columns`);
    const [name, region, live, budget] = row.map((value) => value.trim());
    if (!name || !region || name.length > 120 || region.length > 160) {
      throw new Error(`Venue CSV row ${index + 2} needs a valid name and region`);
    }
    if (names.has(name.toLowerCase())) throw new Error(`Duplicate venue: ${name}`);
    names.add(name.toLowerCase());
    if (live !== "true" && live !== "false") {
      throw new Error(`Venue CSV row ${index + 2}: live_music_allowed must be true or false`);
    }
    if (budget && (!/^\d+$/.test(budget) || !Number.isSafeInteger(Number(budget)))) {
      throw new Error(`Venue CSV row ${index + 2}: budget_limit must be a nonnegative integer or blank`);
    }
    return { name, region, live_music_allowed: live === "true", budget_limit: budget };
  });
}
