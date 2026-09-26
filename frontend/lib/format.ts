// French formatting, matching the mockups: "1 284", "+42 %", "21 sept.".

export const NARROW_NBSP = " ";
const MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
const MONTHS_LONG = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];

/** 1284 -> "1 284" (narrow no-break space). */
export function num(v: number, decimals = 0): string {
  return v
    .toLocaleString("fr-FR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
    .replace(/ | | /g, NARROW_NBSP);
}

/** 0.42 -> "+42 %" (signed) or "42 %"; uses a real minus sign. */
export function pct(ratio: number, signed = false): string {
  const n = Math.round(ratio * 100);
  const sign = signed ? (n > 0 ? "+" : n < 0 ? "−" : "") : "";
  return `${sign}${Math.abs(n)}${NARROW_NBSP}%`;
}

function parse(iso: string): Date {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

/** "2026-09-21" -> "21 sept." */
export function dayShort(iso: string): string {
  const d = parse(iso);
  return `${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

/** "2026-09-21" -> "21 septembre 2026" */
export function dayLong(iso: string): string {
  const d = parse(iso);
  return `${d.getDate()} ${MONTHS_LONG[d.getMonth()]} ${d.getFullYear()}`;
}

/** ISO timestamp -> "il y a 3 h" / "il y a 12 min" / "il y a 2 j". */
export function ago(isoTimestamp: string, now = new Date()): string {
  const minutes = Math.max(0, Math.round((now.getTime() - new Date(isoTimestamp).getTime()) / 60000));
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes}${NARROW_NBSP}min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `il y a ${hours}${NARROW_NBSP}h`;
  return `il y a ${Math.round(hours / 24)}${NARROW_NBSP}j`;
}

/** ISO timestamp -> "26 sept. 2026 · 06:02" */
export function stamp(isoTimestamp: string): string {
  const d = new Date(isoTimestamp);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()} · ${hh}:${mm}`;
}
