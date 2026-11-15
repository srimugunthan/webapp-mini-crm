export function fmtTs(ts: number | null | undefined): string {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/** Compact date for tight tables, e.g. "8 Nov 26"; the full date is in the title attribute where shown. */
export function fmtShort(ts: number | null | undefined): string {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "2-digit" });
}

export function dateInputToEpoch(value: string): number | null {
  if (!value) return null;
  const [y, m, d] = value.split("-").map(Number);
  return Math.floor(new Date(y, m - 1, d, 12).getTime() / 1000);
}

export function epochToDateInput(ts: number | null | undefined): string {
  if (!ts) return "";
  const d = new Date(ts * 1000);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function fullName(c: { first_name: string; last_name: string }): string {
  return `${c.first_name} ${c.last_name}`.trim() || "(no name)";
}

/** Index of the stage reached by moving `delta` steps; null when out of range. */
export function stepStage<T extends { id: number }>(stages: T[], currentId: number | null, delta: 1 | -1): T | null {
  if (!stages.length) return null;
  if (currentId === null) return delta === 1 ? stages[0] : null;
  const i = stages.findIndex((s) => s.id === currentId);
  const j = i + delta;
  return j >= 0 && j < stages.length ? stages[j] : null;
}

/** "All 40 · connected 22 · closed 1" style summary used by chips. */
export function chipLabel(name: string, count: number): string {
  return `${name} ${count}`;
}
