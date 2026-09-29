import Link from "next/link";
import { Suspense } from "react";

import { ChartCard } from "@/components/charts/ChartCard";
import { LineChart, SeriesTable, type Series } from "@/components/charts/LineChart";
import { UrlSelect, UrlTabs } from "@/components/shell/Filters";
import { PageHeader } from "@/components/shell/PageHeader";
import { EmptyState, StatusBadge, Visual } from "@/components/ui";
import { api } from "@/lib/api";
import { swatchPaint } from "@/lib/chroma";
import { dayShort, num, pct } from "@/lib/format";
import { DIMENSIONS, DIMENSION_TABS, STATUS, isDimension, seriesSlots } from "@/lib/taxonomy";

export const metadata = { title: "Tendances" };

const PERIODS = [8, 12, 26];

export default async function TrendsPage({ searchParams }: PageProps<"/tendances">) {
  const q = await searchParams;
  const dim = isDimension(q.dim) ? q.dim : "shape";
  const weeks = PERIODS.includes(Number(q.weeks)) ? Number(q.weeks) : 12;
  const week = typeof q.week === "string" ? q.week : undefined;
  const [meta, data, taxonomy] = await Promise.all([api.meta(), api.trends(dim, weeks, week), api.taxonomy()]);
  const dimLabel = DIMENSION_TABS[dim];
  const order = taxonomy[dim].items.map(i => i.code);

  // Chart: the 6 most-mentioned attributes this week (brief: ≤ 6 series, the rest stays in the table).
  const charted = data.series.filter(s => s.mentions.some(v => v > 0)).slice(0, 6);
  const slots = seriesSlots(charted.map(s => s.code), order);
  const series: Series[] = charted.map(s => ({ id: s.code, label: s.label, values: s.mentions, slot: slots[s.code],
                                               hex: dim === "color" ? s.hex : null, multicolor: dim === "color" && !!s.multicolor }));
  const shares = [...data.series].filter(s => s.share > 0).sort((a, b) => b.share - a.share);
  const maxShare = shares[0]?.share ?? 1;
  const byMomentum = [...data.series].sort((a, b) => b.momentum - a.momentum);
  const weekLabel = data.week ? dayShort(data.week) : "";

  return (
    <PageHeader meta={meta} week={data.week} exportDimension={dim} title="Tendances"
                subtitle={`${dimLabel} · ${weeks} semaines${weekLabel ? ` · semaine du ${weekLabel}` : ""}`}>
      <div className="screen-trends">
        <div className="filter-row">
          <Suspense fallback={null}>
            <UrlTabs param="dim" label="Dimension d'analyse" current={dim}
                     options={DIMENSIONS.map(d => ({ value: d, label: DIMENSION_TABS[d] }))} />
            <label className="period-wrap">
              Période
              <UrlSelect param="weeks" label="Période" current={String(weeks)}
                         options={PERIODS.map(p => ({ value: String(p), label: `${p} semaines` }))} />
            </label>
          </Suspense>
        </div>

        {!data.week || !charted.length ? (
          <EmptyState title="Pas encore de données pour cette dimension">
            Les tendances apparaîtront après la prochaine collecte.
          </EmptyState>
        ) : (
          <>
            <div className="chart-layout">
              <ChartCard className="chart-card" titleId="chartTitle" title="Mentions pondérées par semaine"
                         subtitle={`Top ${charted.length} attributs · ${dimLabel.toLowerCase()} · ${weeks} semaines`}
                         graph={<LineChart weeks={data.weeks} series={series} ariaLabel={`Mentions pondérées par semaine, ${dimLabel.toLowerCase()}`} />}
                         table={<SeriesTable weeks={data.weeks} series={series} caption={`Mentions pondérées par semaine, ${dimLabel.toLowerCase()}`} />} />

              <ChartCard className="share-card" titleId="shareTitle" title="Part de voix cette semaine"
                         subtitle={`Mentions « ${dimLabel.toLowerCase()} » · semaine du ${weekLabel}`}
                         note="Répartition des mentions de la dimension sur la semaine. Les couleurs des barres suivent la légende du graphique."
                         graph={
                           <>
                             <div className="share-rows">
                               {shares.map(s => (
                                 <div key={s.code} className="share-row">
                                   <span className="share-name">
                                     {dim === "color" && (s.hex || s.multicolor) && <span className="swatch" style={{ background: swatchPaint(s) }} aria-hidden="true" />}
                                     <span title={s.label}>{s.label}</span>
                                   </span>
                                   <span className="share-track">
                                     <span className="share-fill" style={{ width: `${(100 * s.share / maxShare).toFixed(1)}%`, background: s.code in slots ? `var(--series-${slots[s.code] + 1})` : "var(--border-strong)" }} />
                                   </span>
                                   <span className="share-val">{pct(s.share)}</span>
                                 </div>
                               ))}
                             </div>
                             {dim === "color" && (
                               <div className="palette-block">
                                 <p className="palette-title">Palette de la semaine</p>
                                 <div className="palette-strip" role="img"
                                      aria-label={`Palette de la semaine : ${shares.map(s => `${s.label} ${Math.round(s.share * 100)} %`).join(", ")}`}>
                                   {shares.map(s => <span key={s.code} className="palette-seg" title={`${s.label} · ${pct(s.share)}`}
                                                          style={{ width: `${(100 * s.share).toFixed(2)}%`, background: swatchPaint(s) ?? "var(--surface-subtle)" }} />)}
                                 </div>
                                 <div className="palette-legend">
                                   {shares.map(s => (
                                     <span key={s.code} className="palette-item">
                                       <span className="swatch" style={{ background: swatchPaint(s) }} aria-hidden="true" />
                                       {s.label} <b>{pct(s.share)}</b>
                                     </span>
                                   ))}
                                 </div>
                               </div>
                             )}
                           </>
                         }
                         table={
                           <div className="table-scroll">
                             <table className="data-table">
                               <caption className="sr-only">Part de voix cette semaine</caption>
                               <thead><tr><th scope="col">Attribut</th><th scope="col" className="numcol">Part</th><th scope="col" className="numcol">Mentions</th></tr></thead>
                               <tbody>
                                 {shares.map(s => (
                                   <tr key={s.code}><th scope="row">{s.label}</th><td className="numcol">{pct(s.share)}</td><td className="numcol">{num(s.mentions[s.mentions.length - 1], 1)}</td></tr>
                                 ))}
                               </tbody>
                             </table>
                           </div>
                         } />
            </div>

            <section className="card table-card" aria-labelledby="tableTitle">
              <div className="card-head">
                <div>
                  <h2 className="card-title" id="tableTitle">Attributs · {dimLabel}</h2>
                  <p className="card-sub">Classés par momentum sur 4 semaines · semaine du {weekLabel}</p>
                </div>
                <span className="pill">{byMomentum.length} attributs</span>
              </div>
              <div className="table-scroll">
                <table className="data-table">
                  <caption className="sr-only">Attributs {dimLabel.toLowerCase()} classés par momentum</caption>
                  <thead>
                    <tr>
                      <th scope="col">Attribut</th><th scope="col" className="numcol">Part</th><th scope="col" className="numcol">Mentions (sem.)</th>
                      <th scope="col">Momentum</th><th scope="col">Statut</th><th scope="col"><span className="sr-only">Détail</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {byMomentum.map(s => (
                      <tr key={s.code}>
                        <th scope="row"><span className="attr-cell"><Visual dimension={dim} attr={s} />{s.label}</span></th>
                        <td className="numcol">{pct(s.share)}</td>
                        <td className="numcol">{num(s.mentions[s.mentions.length - 1], 1)}</td>
                        <td><StatusBadge status={s.status} momentum={s.momentum} tone={s} /></td>
                        <td>{STATUS[s.status].label}</td>
                        <td className="numcol"><Link className="link-more" href={`/tendances/${dim}/${s.code}`} aria-label={`Détail : ${s.label}`}>Détail →</Link></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </div>
    </PageHeader>
  );
}
