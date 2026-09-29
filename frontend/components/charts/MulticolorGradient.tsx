import { MULTICOLOR_STOPS } from "@/lib/chroma";

/** SVG spectrum for a "Multicolore" line, from x1 to x2 in the chart's own units. userSpaceOnUse on purpose: an
 *  objectBoundingBox gradient paints nothing on a perfectly flat line (its box has no height). Server-safe. */
export function MulticolorGradient({ id, x1, x2 }: { id: string; x1: number; x2: number }) {
  return (
    <defs>
      <linearGradient id={id} gradientUnits="userSpaceOnUse" x1={x1} x2={x2} y1={0} y2={0}>
        {MULTICOLOR_STOPS.map((c, i) => <stop key={c} offset={i / (MULTICOLOR_STOPS.length - 1)} stopColor={c} />)}
      </linearGradient>
    </defs>
  );
}
