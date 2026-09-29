import Link from "next/link";
import { notFound } from "next/navigation";

import { ChartCard } from "@/components/charts/ChartCard";
import { LineChart, SeriesTable, type Series } from "@/components/charts/LineChart";
import { FrequentPairings } from "@/components/FrequentPairings";
import { Glyph } from "@/components/Glyph";
import { Icon } from "@/components/icons";
import { RetailPresence } from "@/components/RetailPresence";
import { PageHeader } from "@/components/shell/PageHeader";
import { KpiTile, LangPill, StatusBadge } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { swatchPaint } from "@/lib/chroma";
import { dayLong, dayShort, num, pct } from "@/lib/format";
import { KIND_LABELS, STATUS, isDimension } from "@/lib/taxonomy";
import type { Stance } from "@/lib/types";

const STANCES: { key: Stance; label: string; hint: string; color: string }[] = [
  { key: "rising", label: "En hausse", hint: "l'extrait décrit une tendance qui progresse", color: "var(--status-up)" },
  { key: "neutral", label: "Neutre", hint: "mention descriptive, sans jugement de tendance", color: "var(--status-stable)" },
  { key: "declining", label: "En recul", hint: "l'extrait annonce un essoufflement", color: "var(--status-down)" },
];
const STANCE_CHIP: Record<Stance, string> = { rising: "en hausse", neutral: "neutre", declining: "en recul" };

export async function generateMetadata({ params }: PageProps<"/tendances/[dimension]/[code]">) {
  const { dimension, code } = await params;
  const taxonomy = await api.taxonomy().catch(() => null);
  const label = isDimension(dimension) ? taxonomy?.[dimension].items.find(i => i.code === code)?.label : undefined;
  return { title: label ? `${label} · Tendances` : "Tendances" };
}

export default async function TrendDetailPage({ params, searchParams }: PageProps<"/tendances/[dimension]/[code]">) {
  const { dimension, code } = await params;
  const { week: weekParam } = await searchParams;
  if (!isDimension(dimension)) notFound();
  const week = typeof weekParam === "string" ? weekParam : undefined;
  const [meta, d] = await Promise.all([
    api.meta(),
    api.trendDetail(dimension, code, week).catch(e => {
      if (e instanceof ApiError && e.status === 404) notFound();
      throw e;
    }),
  ]);

  const status = STATUS[d.status];
  const n = d.mentions.length;
  const prev = n >= 2 ? d.mentions[n - 1] - d.mentions[n - 2] : 0;
  const stanceTotal = d.stance.rising + d.stance.neutral + d.stance.declining;
  const brandsTotal = d.brands.reduce((s, b) => s + b.count, 0);
  const frValues = d.search.fr.filter((v): v is number => v != null);
  const searchDelta = frValues.length >= 2 ? frValues[frValues.length - 1] - frValues[0] : null;
  const subtitle = d.status === "en_hausse" && d.rising_streak > 1
    ? `${d.dimension_label} · en hausse depuis ${d.rising_streak} semaines`
    : `${d.dimension_label} · ${status.label.toLowerCase()}`;

  // Color trends are drawn in their real hex; the two search series then share it (France solid, Monde dashed).
  const hex = dimension === "color" ? d.hex : null;
  const multicolor = dimension === "color" && !!d.multicolor;
  const mentionsSeries: Series[] = [{ id: "mentions", label: "Mentions", values: d.mentions, slot: 0, hex, multicolor }];
  const searchSeries: Series[] = [
    { id: "fr", label: meta.market_geo === "FR" ? "France" : meta.market_geo, values: d.search.fr, slot: 0, hex, multicolor },
    { id: "world", label: "Monde", values: d.search.world, slot: 1, hex, multicolor, dash: !!hex || multicolor },
  ];
  const hasSearch = searchSeries.some(s => s.values.some(v => v != null));

  return (
    <PageHeader meta={meta} week={d.week} exportDimension={dimension} title="Tendances"
                subtitle={`Détail d'une tendance${d.week ? ` · semaine du ${dayShort(d.week)}` : ""}`}>
      <div className="screen-detail">
        <Link className="back-link" href={`/tendances?dim=${dimension}`}><Icon name="arrowLeft" />Toutes les tendances</Link>

        <section className="card detail-head" aria-labelledby="detailTitle">
          {dimension === "shape" ? <Glyph code={d.code} className="detail-glyph" />
            : dimension === "color" && (d.hex || d.multicolor) ? <span className="detail-glyph"><span className="swatch" style={{ background: swatchPaint(d), width: 28, height: 28 }} /></span>
            : <span className="detail-glyph"><span className="neutral-dot" /></span>}
          <div>
            <div className="detail-title-row">
              <h2 className="detail-title" id="detailTitle">{d.label}</h2>
              <StatusBadge status={d.status} momentum={d.momentum} tone={d} />
            </div>
            <p className="detail-sub">{subtitle}</p>
          </div>
        </section>

        {/* Two lenses, side by side in the buyer's reading order: global momentum (leading) vs local shelves (lagging). */}
        <div className="lens-head" id="lensSignal">
          <h2 className="lens-title">Signal International (Presse)</h2>
          <span className="pill lens-tag">Indicateur avancé</span>
          <p className="lens-note">
            Élan mondial : presse optique et mode, France et international, et recherches Google en France.
            Ce qui arrive sur le marché.
          </p>
        </div>

        <section className="kpi-grid" aria-label="Statistiques de la tendance">
          <KpiTile label="Mentions cette semaine" value={num(d.stats.this_week, Number.isInteger(d.stats.this_week) ? 0 : 1)}
                   detail={`${prev >= 0 ? "+" : "−"}${num(Math.abs(prev), Number.isInteger(prev) ? 0 : 1)} vs sem. précédente`} icon={prev >= 0 ? "up" : undefined} />
          <KpiTile label="Moyenne 4 sem." value={d.stats.avg_4w == null ? "–" : num(d.stats.avg_4w, 1)} detail="4 semaines précédentes" icon="clock" />
          <KpiTile label={`Part des ${d.dimension_label.toLowerCase().startsWith("forme") ? "formes" : d.dimension_label.toLowerCase()}`}
                   value={pct(d.stats.share)} detail="des mentions de la dimension" icon="globe" />
          <KpiTile label={`Intérêt de recherche ${meta.market_geo}`} value={d.stats.search_fr == null ? "–" : `${num(d.stats.search_fr)}/100`}
                   detail={searchDelta == null ? "Google Trends" : `${searchDelta >= 0 ? "+" : "−"}${num(Math.abs(searchDelta))} pts en ${n} sem.`}
                   icon={searchDelta != null && searchDelta >= 0 ? "up" : undefined} />
        </section>

        {/* Two separate charts: mentions and search interest are never on a dual axis (brief rule 2). */}
        <section className="charts-grid" aria-label="Graphiques de la tendance">
          <ChartCard className="chart-card" titleId="chartMentionsTitle" title="Mentions par semaine" subtitle={`Mentions pondérées · ${n} semaines`}
                     graph={<LineChart weeks={d.weeks} series={mentionsSeries} legend={false} ariaLabel={`Mentions hebdomadaires de ${d.label}, ${n} semaines`} />}
                     table={<SeriesTable weeks={d.weeks} series={mentionsSeries} caption={`Mentions hebdomadaires de ${d.label}`} />} />
          <ChartCard className="chart-card" titleId="chartSearchTitle" title="Intérêt de recherche Google" subtitle={`Échelle relative de 0 à 100 · ${n} semaines`}
                     graph={hasSearch
                       ? <LineChart weeks={d.weeks} series={searchSeries} yMax={100} ariaLabel={`Intérêt de recherche Google pour ${d.label}, ${searchSeries[0].label} et Monde`} />
                       : <p className="section-note">Pas encore de données Google Trends pour cet attribut.</p>}
                     table={<SeriesTable weeks={d.weeks} series={searchSeries} caption={`Intérêt de recherche Google (0 à 100) pour ${d.label}`} />} />
        </section>

        <section className="detail-grid">
          <article className="card" aria-labelledby="toneTitle">
            <div className="trend-card-head">
              <h3 className="trend-card-title" id="toneTitle">Tonalité des mentions</h3>
              <span className="section-note">Basée sur {num(stanceTotal)} mention{stanceTotal > 1 ? "s" : ""} (4 sem.)</span>
            </div>
            {stanceTotal > 0 ? (
              <>
                <div className="stack-bar" role="img"
                     aria-label={`Tonalité des mentions : ${STANCES.map(s => `${Math.round(100 * d.stance[s.key] / stanceTotal)} % ${s.label.toLowerCase()}`).join(", ")}`}>
                  {STANCES.map(s => d.stance[s.key] > 0 && <span key={s.key} style={{ width: `${(100 * d.stance[s.key] / stanceTotal).toFixed(1)}%`, background: s.color }} />)}
                </div>
                <ul className="stack-legend">
                  {STANCES.map(s => (
                    <li key={s.key}><span className="dot" style={{ background: s.color }} />{s.label} — {s.hint}<strong className="num">{pct(d.stance[s.key] / stanceTotal)}</strong></li>
                  ))}
                </ul>
              </>
            ) : <p className="section-note">Aucune mention sur les 4 dernières semaines.</p>}
          </article>

          <article className="card" aria-labelledby="brandsTitle">
            <div className="trend-card-head">
              <h3 className="trend-card-title" id="brandsTitle">Marques citées</h3>
              <span className="section-note">{d.brands.length} marque{d.brands.length > 1 ? "s" : ""} · {num(brandsTotal)} mention{brandsTotal > 1 ? "s" : ""}</span>
            </div>
            {d.brands.length ? (
              <div className="chip-row">
                {d.brands.map(b => <span key={b.name} className="chip">{b.name} <span className="chip-count num">{b.count}</span></span>)}
              </div>
            ) : <p className="section-note">Aucune marque citée avec cet attribut.</p>}
          </article>
        </section>

        <RetailPresence d={d} />
        <FrequentPairings d={d} />

        <section aria-labelledby="evidenceTitle">
          <div className="section-head">
            <h2 className="section-title" id="evidenceTitle">Sources à l&apos;appui (presse)</h2>
            <span className="section-note">{d.evidence.length} extrait{d.evidence.length > 1 ? "s" : ""} citant « {d.label.toLowerCase()} »</span>
          </div>
          <div className="source-cards">
            {d.evidence.map((m, i) => (
              <article key={`${m.url}-${i}`} className="card source-card">
                <div className="source-card-head">
                  <span className="source-name">{m.source}</span>
                  <span className="source-date">{dayLong(m.date)}</span>
                  <LangPill lang={m.lang} />
                  <span className="pill">{KIND_LABELS[m.kind] ?? m.kind}</span>
                  {m.url.startsWith("http") && (
                    <a className="source-ext" href={m.url} target="_blank" rel="noopener noreferrer" aria-label={`Ouvrir l'article ${m.source} (nouvel onglet)`}>
                      <Icon name="external" />
                    </a>
                  )}
                </div>
                <blockquote className="source-quote-full">« {m.evidence} »</blockquote>
                {m.summary && <p className="source-ai"><span className="source-ai-label">Résumé IA</span>{m.summary}</p>}
                <div className="chip-row">
                  <span className="chip">{d.dimension_label} · {d.label}</span>
                  <span className="chip">Tonalité · {STANCE_CHIP[m.stance]}</span>
                </div>
              </article>
            ))}
            {!d.evidence.length && <p className="section-note">Aucun extrait pour l&apos;instant.</p>}
          </div>
        </section>
      </div>
    </PageHeader>
  );
}
