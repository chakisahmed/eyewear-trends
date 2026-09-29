"use client";

import { useState, type ReactNode } from "react";

import { Icon } from "@/components/icons";
import { guardStyle, lineColor } from "@/lib/chroma";
import { dayShort, num } from "@/lib/format";

const W = 260, H = 116, PL = 22, PR = 34, PT = 10, PB = 18;
const PW = W - PL - PR, PH = H - PT - PB;

const hasVolume = (vals: (number | null)[]) => vals.some(v => v != null && v > 0);

/** Change of the mean of the last 4 weeks vs the 4 before, as text: "+12 %", "nouveau" (up from 0) or "—". */
function change4w(vals: (number | null)[]): string {
  const avg = (xs: (number | null)[]) => {
    const ok = xs.filter((v): v is number => v != null);
    return ok.length ? ok.reduce((a, b) => a + b, 0) / ok.length : null;
  };
  const recent = avg(vals.slice(-4)), base = avg(vals.slice(-8, -4));
  if (recent == null || base == null) return "—";
  if (!base) return recent > 0 ? "nouveau" : "—";
  const c = Math.round(((recent - base) / base) * 100);
  return `${c > 0 ? "+" : c < 0 ? "−" : ""}${Math.abs(c)} %`;
}

/** Demand card: France vs Monde Google Trends interest on a FIXED 0–100 scale (100 = the keyword's own
 *  peak; same scale on every card, never stretched), direct end labels, and a table view with the same
 *  numbers. A series with no volume at all (below Google's threshold) is not drawn as a fake flat 0. */
export function MiniDemandCard({ head, label, weeks, fr: frIn, world: worldIn, geoLabel, hex }: {
  head: ReactNode; label: string; weeks: string[]; fr: (number | null)[]; world: (number | null)[]; geoLabel: string;
  /** Real frame color (color dimension): both lines use it, France solid and Monde dashed. */
  hex?: string | null;
}) {
  const [asTable, setAsTable] = useState(false);
  const real = lineColor(hex);
  const frColor = real ?? "var(--series-1)", worldColor = real ?? "var(--series-2)";
  const worldDash = real ? "6 4" : undefined;
  const n = weeks.length;
  const none = weeks.map(() => null);
  const fr = hasVolume(frIn) ? frIn : none, world = hasVolume(worldIn) ? worldIn : none;
  const empty = !hasVolume(fr) && !hasVolume(world);
  const [changeGeo, change] = hasVolume(fr) ? [geoLabel, change4w(fr)] : [ "Monde", change4w(world)];
  const X = (i: number) => PL + (n <= 1 ? 0 : (i * PW) / (n - 1));
  const Y = (v: number) => PT + ((100 - v) / 100) * PH;
  const poly = (vals: (number | null)[]) =>
    vals.map((v, i) => (v == null ? null : `${X(i).toFixed(1)},${Y(v).toFixed(1)}`)).filter(Boolean).join(" ");
  const last = (vals: (number | null)[]) => {
    for (let i = vals.length - 1; i >= 0; i--) if (vals[i] != null) return { i, v: vals[i] as number };
    return null;
  };
  const lf = last(fr), lw = last(world);
  let yf = lf ? Y(lf.v) : 0, yw = lw ? Y(lw.v) : 0;
  if (lf && lw && Math.abs(yf - yw) < 11) { if (yf <= yw) { yf -= 5.5; yw += 5.5; } else { yf += 5.5; yw -= 5.5; } }

  return (
    <article className="card demand-card">
      <div className="demand-card-head">{head}</div>
      <div className="mini-chart">
        {empty ? (
          <p className="mini-empty">Volume de recherche trop faible pour Google Trends</p>
        ) : asTable ? (
          <div className="mini-table-wrap">
            <table className="mini-table">
              <caption>Intérêt de recherche hebdomadaire (0–100) — {label}</caption>
              <thead><tr><th scope="col">Semaine</th><th scope="col">{geoLabel}</th><th scope="col">Monde</th></tr></thead>
              <tbody>
                {weeks.map((w, i) => (
                  <tr key={w}><th scope="row">Sem. du {dayShort(w)}</th><td>{fr[i] ?? "–"}</td><td>{world[i] ?? "–"}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="mini-svg-wrap">
            <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Intérêt de recherche sur ${n} semaines pour ${label}, ${geoLabel} et Monde, échelle 0 à 100`}>
              {[0, 50, 100].map(g => (
                <g key={g}>
                  <line className="grid-line" x1={PL} x2={PL + PW} y1={Y(g)} y2={Y(g)} />
                  <text x={PL - 5} y={Y(g) + 3} textAnchor="end" fontSize={8.5}>{g}</text>
                </g>
              ))}
              {n > 0 && <text x={PL} y={H - 4} fontSize={8.5}>{dayShort(weeks[0])}</text>}
              {n > 1 && <text x={PL + PW} y={H - 4} textAnchor="end" fontSize={8.5}>{dayShort(weeks[n - 1])}</text>}
              {real && <polyline className="halo" style={guardStyle(real)} points={poly(world)} strokeWidth={4.5} strokeDasharray={worldDash} />}
              <polyline points={poly(world)} fill="none" stroke={worldColor} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={worldDash} />
              {real && <polyline className="halo" style={guardStyle(real)} points={poly(fr)} strokeWidth={4.5} />}
              <polyline points={poly(fr)} fill="none" stroke={frColor} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
              {lf && <circle cx={X(lf.i)} cy={Y(lf.v)} r={2.5} fill={frColor} className={real ? "halo-ring" : undefined} style={guardStyle(real)} />}
              {lw && <circle cx={X(lw.i)} cy={Y(lw.v)} r={2.5} fill={worldColor} className={real ? "halo-ring" : undefined} style={guardStyle(real)} />}
              {lf && <text className="end-label" x={PL + PW + 5} y={yf + 3} fontSize={9}>{num(lf.v)}</text>}
              {lw && <text className="end-label" x={PL + PW + 5} y={yw + 3} fontSize={9}>{num(lw.v)}</text>}
            </svg>
          </div>
        )}
        {!empty && (
          <p className="search-change">
            Recherche (4 sem.) : <strong>{change}</strong> · {changeGeo}
          </p>
        )}
        {!empty && (
          <div className="mini-foot">
            <div className="mini-legend">
              <span className="legend-item"><span className={real ? "legend-line halo-dot" : "legend-line"} style={{ ["--c" as string]: frColor, ...guardStyle(real) }} />{geoLabel}</span>
              <span className="legend-item"><span className={real ? "legend-line halo-dot" : "legend-line"}
                    style={{ ["--c" as string]: worldColor, ...(real ? { background: `repeating-linear-gradient(90deg, ${real} 0 4px, transparent 4px 6px)` } : {}), ...guardStyle(real) }} />Monde</span>
            </div>
            <button type="button" className="btn btn-secondary btn-sm view-toggle" aria-pressed={asTable} onClick={() => setAsTable(!asTable)}>
              <Icon name={asTable ? "demand" : "fileTable"} />
              <span>{asTable ? "Vue graphique" : "Vue tableau"}</span>
            </button>
          </div>
        )}
      </div>
    </article>
  );
}
