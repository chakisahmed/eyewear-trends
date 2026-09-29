// Small display components shared by every screen (all server-safe).
import Link from "next/link";
import { useId, type ReactNode } from "react";

import { MulticolorGradient } from "@/components/charts/MulticolorGradient";
import { guardStyle, lineColor, swatchPaint } from "@/lib/chroma";
import { pct, NARROW_NBSP } from "@/lib/format";
import { STATUS } from "@/lib/taxonomy";
import type { Attribute, Dimension, Status, Tone } from "@/lib/types";

import { Glyph } from "./Glyph";
import { Icon } from "./icons";

/** Glyph for shapes, real swatch for colors (ringed so white/clear stay visible), neutral dot otherwise. */
export function Visual({ dimension, attr }: { dimension: Dimension; attr: Attribute }) {
  if (dimension === "shape") return <Glyph code={attr.code} />;
  if (dimension === "color" && (attr.hex || attr.multicolor)) {
    return <span className="trend-visual"><span className="swatch" style={{ background: swatchPaint(attr) }} /></span>;
  }
  return <span className="trend-visual"><span className="neutral-dot" /></span>;
}

/** Status badge: icon (status color) + value (text color, AA contrast). Tone-driven declines say why. */
export function StatusBadge({ status, momentum, tone }: { status: Status; momentum: number; tone?: Partial<Tone> }) {
  const st = STATUS[status];
  const fading = status === "en_baisse" && tone?.decline_reason === "tonalite" && tone.decline_share != null;
  // Too little data: no percentage at all (a +300 % on 3 mentions would mislead buyers).
  const value = status === "faible" ? "Peu de données"
    : fading ? `${pct(tone!.decline_share!)} d'avis en recul` : pct(momentum, true);
  return (
    <span className={`badge badge-${st.variant}`} title={st.label}>
      <Icon name={st.variant} strokeWidth={2.4} />
      {value}
      {status !== "faible" && <span className="sr-only"> · {st.label}</span>}
    </span>
  );
}

/** 8-week sparkline. Scale rule from the brief: range ≥ 60 % of the peak, centered, never below 0,
 *  so a stable 8, 8, 9, 8 looks flat while 3 → 14 fills the height. */
export function Sparkline({ values, label, width = 72, height = 24, className = "spark", hex, multicolor = false }: {
  values: number[]; label: string; width?: number; height?: number; className?: string;
  /** Real frame color for the color dimension: the line inherits it (with a contrast halo where needed). */
  hex?: string | null;
  /** "Multicolore" family: the line is a spectrum instead of its hex. */
  multicolor?: boolean;
}) {
  const gradientId = `mc${useId().replace(/[^\w-]/g, "")}`;
  const pts = values.length > 1 ? values : [values[0] ?? 0, values[0] ?? 0];
  const p = 3, lo = Math.min(...pts), hi = Math.max(...pts);
  const span = Math.max(hi - lo, 0.6 * hi, 1);
  const min = Math.max(0, (hi + lo) / 2 - span / 2);
  const step = (width - 2 * p) / (pts.length - 1);
  const coords = pts.map((v, i) => [p + i * step, height - p - ((v - min) / span) * (height - 2 * p)]);
  const last = coords[coords.length - 1];
  const line = coords.map(c => c.map(n => n.toFixed(2)).join(",")).join(" ");
  const real = lineColor(hex);
  const tinted = multicolor || !!real;
  const stroke = multicolor ? `url(#${gradientId})` : real ?? "var(--series-1)";
  return (
    <svg className={className} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label} style={guardStyle(real, multicolor)}>
      {multicolor && <MulticolorGradient id={gradientId} x1={p} x2={width - p} />}
      {tinted && <polyline className="halo" points={line} strokeWidth={4.5} />}
      <polyline points={line} fill="none" stroke={stroke} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={last[0]} cy={last[1]} r={2.5} fill={stroke} className={tinted ? "halo-ring" : undefined} />
    </svg>
  );
}

export function TrendRowLink({ href, dimension, row, spark, status, momentum, tone }: {
  href: string; dimension: Dimension; row: Attribute; spark: number[]; status: Status; momentum: number; tone?: Partial<Tone>;
}) {
  return (
    <Link className="trend-row" href={href}>
      <Visual dimension={dimension} attr={row} />
      <span className="trend-label">{row.label}</span>
      <Sparkline values={spark} hex={dimension === "color" ? row.hex : null} multicolor={dimension === "color" && !!row.multicolor}
                 label={`${row.label} : tendance sur ${spark.length} semaines, ${STATUS[status].label.toLowerCase()}`} />
      <StatusBadge status={status} momentum={momentum} tone={tone} />
    </Link>
  );
}

export function KpiTile({ label, value, detail, icon }: { label: string; value: string; detail?: string; icon?: "up" | "globe" | "clock" }) {
  return (
    <div className="card kpi-tile">
      <p className="kpi-label">{label}</p>
      <p className="kpi-value num">{value}</p>
      {detail && (
        <p className="kpi-detail">
          {icon && <Icon name={icon} className={icon === "up" ? "up" : undefined} strokeWidth={icon === "up" ? 2.4 : 2} />}
          {detail}
        </p>
      )}
    </div>
  );
}

export function EmptyState({ title, children, actions }: { title: string; children?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="card empty-state">
      <Icon name="sparkle" />
      <h2>{title}</h2>
      {children && <p>{children}</p>}
      {actions && <div className="empty-actions">{actions}</div>}
    </div>
  );
}

export function LangPill({ lang }: { lang: string }) {
  return <span className="lang-pill">{lang.toUpperCase()}</span>;
}

export const nbsp = NARROW_NBSP;
