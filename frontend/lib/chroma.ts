// Chromatic fidelity for charts: a color trend is drawn in its real (Palier 2) hex. A frame color can vanish
// against the card it is drawn on (ivory or clear on white, black or tortoiseshell on the dark card), so each
// hex is checked against both card backgrounds and given a contrasting halo only where it would not read.
import type { CSSProperties } from "react";

/** The card surface the charts sit on, in each theme (--surface-card in shared.css). */
const CARD = { light: "#FFFFFF", dark: "#1A1D21" } as const;

/** WCAG 1.4.11: a graphical object needs at least 3:1 against its background. */
export const MIN_CONTRAST = 3;

function channels(hex: string): [number, number, number] | null {
  const m = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return null;
  const h = m[1].length === 3 ? [...m[1]].map(c => c + c).join("") : m[1];
  return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16)) as [number, number, number];
}

/** WCAG relative luminance, 0 (black) to 1 (white); null when the hex is unusable. */
export function luminance(hex: string): number | null {
  const rgb = channels(hex);
  if (!rgb) return null;
  const [r, g, b] = rgb.map(v => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrast(a: string, b: string): number | null {
  const la = luminance(a), lb = luminance(b);
  if (la == null || lb == null) return null;
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

/** Which themes need a contrast halo for this line color. */
export function guard(hex: string): { light: boolean; dark: boolean } {
  const low = (bg: string) => (contrast(hex, bg) ?? MIN_CONTRAST) < MIN_CONTRAST;
  return { light: low(CARD.light), dark: low(CARD.dark) };
}

/** Inline custom properties read by `.halo` / `.halo-ring` in shared.css, which switch the halo on per theme. */
export function guardStyle(hex: string | null | undefined): CSSProperties | undefined {
  if (!hex) return undefined;
  const g = guard(hex);
  return { ["--need-l" as string]: g.light ? 1 : 0, ["--need-d" as string]: g.dark ? 1 : 0 };
}

/** A usable "#rrggbb" line color, or null (unknown or malformed hex falls back to the palette). */
export function lineColor(hex: string | null | undefined): string | null {
  return hex && channels(hex) ? hex : null;
}
