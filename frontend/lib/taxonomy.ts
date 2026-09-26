import type { Dimension, SourceKind, Status } from "./types";

export const DIMENSIONS: Dimension[] = ["shape", "color", "material", "style"];

export const DIMENSION_TABS: Record<Dimension, string> = {
  shape: "Formes",
  color: "Couleurs",
  material: "Matières",
  style: "Styles",
};

export function isDimension(v: unknown): v is Dimension {
  return typeof v === "string" && (DIMENSIONS as string[]).includes(v);
}

/** API status -> badge variant (shared.css .badge-up/-peak/-stable/-down) and French label. */
export const STATUS: Record<Status, { variant: "up" | "peak" | "stable" | "down"; label: string }> = {
  en_hausse: { variant: "up", label: "En hausse" },
  au_pic: { variant: "peak", label: "Au pic" },
  stable: { variant: "stable", label: "Stable" },
  en_baisse: { variant: "down", label: "En baisse" },
};

export const KIND_LABELS: Record<SourceKind, string> = {
  press: "Presse",
  news: "Actualités",
  store: "Boutique",
  social: "Réseaux sociaux",
};

/** Six chart series slots (shared.css --series-1…6), assigned in taxonomy order within a chart,
 *  so a color follows its attribute rather than its rank. */
export function seriesSlots(codes: string[], taxonomyOrder: string[]): Record<string, number> {
  const ordered = [...codes].sort((a, b) => taxonomyOrder.indexOf(a) - taxonomyOrder.indexOf(b));
  return Object.fromEntries(ordered.map((c, i) => [c, i % 6]));
}
