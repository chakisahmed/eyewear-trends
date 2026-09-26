"use client";

import { useMemo, useState } from "react";

import { dayShort, num } from "@/lib/format";

export interface Series {
  id: string;
  label: string;
  values: (number | null)[];
  /** 0–5 → var(--series-N): fixed per entity, never by rank. */
  slot: number;
  /** Real frame color, shown as a swatch in the legend only (never as the line color). */
  hex?: string | null;
}

const W = 720, H = 300, M = { t: 14, r: 118, b: 30, l: 34 };
const color = (slot: number) => `var(--series-${slot + 1})`;

/** Hand-written SVG line chart (brief rules): ≤ 6 series, one y-axis, recessive grid, direct labels
 *  when ≤ 4 series are visible, crosshair + tooltip listing every series (mouse and ← / → keys). */
export function LineChart({ weeks, series, yMax, legend = true, ariaLabel, valueSuffix = "" }: {
  weeks: string[];
  series: Series[];
  /** Fixed top of the scale (e.g. 100 for Google Trends); otherwise a rounded max of the data. */
  yMax?: number;
  legend?: boolean;
  ariaLabel: string;
  valueSuffix?: string;
}) {
  const [hidden, setHidden] = useState<Record<string, boolean>>({});
  const [focus, setFocus] = useState<number | null>(null);
  const visible = series.filter(s => !hidden[s.id]);
  const n = weeks.length;
  const iw = W - M.l - M.r, ih = H - M.t - M.b;

  const { top, step } = useMemo(() => {
    if (yMax) return { top: yMax, step: yMax / 4 };
    const max = Math.max(1, ...visible.flatMap(s => s.values.filter((v): v is number => v != null)));
    const st = max <= 10 ? 2 : max <= 25 ? 5 : max <= 60 ? 10 : 20;
    return { top: Math.ceil(max / st) * st, step: st };
  }, [visible, yMax]);

  const x = (i: number) => M.l + (n <= 1 ? 0 : (i * iw) / (n - 1));
  const y = (v: number) => M.t + ih - (v / top) * ih;
  const every = n <= 8 ? 1 : n <= 12 ? 2 : 4;

  type EndLabel = { s: Series; i: number; v: number; y: number };
  const ends: EndLabel[] = [];
  if (visible.length <= 4) {
    for (const s of visible) {
      for (let i = s.values.length - 1; i >= 0; i--) {
        const v = s.values[i];
        if (v != null) { ends.push({ s, i, v, y: y(v) }); break; }
      }
    }
    ends.sort((a, b) => a.y - b.y);
    for (let k = 1; k < ends.length; k++) ends[k].y = Math.max(ends[k].y, ends[k - 1].y + 14); // no overlaps
  }

  function indexAt(clientX: number, box: DOMRect) {
    const sx = ((clientX - box.left) / box.width) * W;
    return Math.max(0, Math.min(n - 1, Math.round(((sx - M.l) / iw) * (n - 1))));
  }
  // Tooltip position as a percentage of the chart width: no DOM measuring needed.
  const tipPct = focus == null ? 0 : (x(focus) / W) * 100;

  return (
    <>
      <div className="chart-wrap">
        <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel}>
          {Array.from({ length: Math.round(top / step) + 1 }, (_, k) => k * step).map(g => (
            <g key={g}>
              <line className={g === 0 ? "base" : "grid"} x1={M.l} x2={W - M.r} y1={y(g)} y2={y(g)} />
              <text className="axis" x={M.l - 8} y={y(g) + 4} textAnchor="end">{num(g)}</text>
            </g>
          ))}
          {weeks.map((w, i) => (n - 1 - i) % every === 0 && (
            <text key={w} className="axis" x={x(i)} y={H - 8} textAnchor="middle">{dayShort(w)}</text>
          ))}
          {visible.map(s => (
            <polyline key={s.id} fill="none" stroke={color(s.slot)} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"
                      points={s.values.map((v, i) => (v == null ? null : `${x(i).toFixed(1)},${y(v).toFixed(1)}`)).filter(Boolean).join(" ")} />
          ))}
          {ends.map(e => (
            <g key={e.s.id}>
              <circle cx={x(e.i)} cy={y(e.v)} r={3} fill={color(e.s.slot)} />
              <text className="end-label" x={x(e.i) + 8} y={e.y + 4}>{e.s.label} · {num(e.v, Number.isInteger(e.v) ? 0 : 1)}</text>
            </g>
          ))}
          {focus != null && (
            <g>
              <line className="cross-line" x1={x(focus)} x2={x(focus)} y1={M.t} y2={M.t + ih} />
              {visible.map(s => s.values[focus] != null && (
                <circle key={s.id} cx={x(focus)} cy={y(s.values[focus] as number)} r={4} fill={color(s.slot)}
                        stroke="var(--surface-card)" strokeWidth={2} />
              ))}
            </g>
          )}
          <rect x={M.l} y={M.t} width={iw} height={ih} fill="transparent" tabIndex={0}
                aria-label="Parcourir les semaines avec les flèches gauche et droite"
                onMouseMove={e => setFocus(indexAt(e.clientX, e.currentTarget.ownerSVGElement!.getBoundingClientRect()))}
                onMouseLeave={() => setFocus(null)}
                onFocus={() => setFocus(f => f ?? n - 1)}
                onBlur={() => setFocus(null)}
                onKeyDown={e => {
                  if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
                  e.preventDefault();
                  setFocus(f => Math.max(0, Math.min(n - 1, (f ?? n - 1) + (e.key === "ArrowRight" ? 1 : -1))));
                }} />
        </svg>
        {focus != null && (
          <div className={`chart-tip${tipPct > 50 ? " flip" : ""}`} style={{ left: `${tipPct}%` }}>
            <p className="tip-title">Semaine du {dayShort(weeks[focus])}</p>
            {[...visible].sort((a, b) => (b.values[focus] ?? -1) - (a.values[focus] ?? -1)).map(s => (
              <div key={s.id} className="tip-row">
                <span className="tip-dot" style={{ background: color(s.slot) }} />
                <span className="tip-name">{s.label}</span>
                <span className="tip-val">{s.values[focus] == null ? "–" : `${num(s.values[focus] as number, Number.isInteger(s.values[focus]) ? 0 : 1)}${valueSuffix}`}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      {legend && series.length > 1 && (
        <div className="legend" aria-label="Légende : cliquer pour afficher ou masquer une série">
          {series.map(s => (
            <button key={s.id} type="button" className="legend-item" aria-pressed={!hidden[s.id]}
                    onClick={() => {
                      if (!hidden[s.id] && visible.length === 1) return; // keep at least one series
                      setHidden(h => ({ ...h, [s.id]: !h[s.id] }));
                    }}>
              <span className="legend-line" style={{ background: color(s.slot) }} aria-hidden="true" />
              {s.hex && <span className="swatch" style={{ background: s.hex }} aria-hidden="true" />}
              {s.label}
            </button>
          ))}
        </div>
      )}
    </>
  );
}

/** The same data as an accessible table ("Vue tableau"). */
export function SeriesTable({ weeks, series, caption, valueSuffix = "" }: {
  weeks: string[]; series: Series[]; caption: string; valueSuffix?: string;
}) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            <th scope="col">Semaine</th>
            {series.map(s => <th key={s.id} scope="col" className="numcol">{s.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {weeks.map((w, i) => ({ w, i })).reverse().map(({ w, i }) => (
            <tr key={w}>
              <th scope="row">{dayShort(w)}</th>
              {series.map(s => (
                <td key={s.id} className="numcol">{s.values[i] == null ? "–" : `${num(s.values[i] as number, Number.isInteger(s.values[i]) ? 0 : 1)}${valueSuffix}`}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
