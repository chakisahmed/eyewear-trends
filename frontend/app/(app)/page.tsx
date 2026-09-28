import Link from "next/link";

import { Icon } from "@/components/icons";
import { LoadDemoButton } from "@/components/shell/HeaderActions";
import { PageHeader } from "@/components/shell/PageHeader";
import { ShelfGaps } from "@/components/ShelfGaps";
import { SummaryBody } from "@/components/Summary";
import { EmptyState, KpiTile, LangPill, TrendRowLink } from "@/components/ui";
import { api } from "@/lib/api";
import { dayShort, num } from "@/lib/format";
import { DIMENSIONS, DIMENSION_TABS } from "@/lib/taxonomy";

export default async function OverviewPage({ searchParams }: PageProps<"/">) {
  const { week: weekParam } = await searchParams;
  const week = typeof weekParam === "string" ? weekParam : undefined;
  const [meta, overview, latest, shelf] = await Promise.all([
    api.meta(), api.overview(week), api.sources({ limit: 4 }),
    api.retailOverview(week).catch(() => null),  // optional block: the overview must not fail without it
  ]);
  const current = overview.week;

  return (
    <PageHeader meta={meta} week={current} title="Vue d'ensemble"
                subtitle={current ? `Tendances lunettes · semaine du ${dayShort(current)}` : "Tendances lunettes"}>
      {!current ? (
        <EmptyState title="Aucune donnée pour l'instant" actions={<LoadDemoButton />}>
          Lancez la première collecte avec « Actualiser les données », ou chargez des données de démonstration
          pour découvrir le tableau de bord.
        </EmptyState>
      ) : (
        <>
          <section className="kpi-grid" aria-label="Indicateurs clés">
            <KpiTile label="Articles analysés" value={num(overview.stats.documents)} detail="articles avec tendances détectées" icon="up" />
            <KpiTile label="Mentions d'attributs" value={num(overview.stats.mentions)} detail="formes, couleurs, matières, styles" icon="up" />
            <KpiTile label="Sources suivies" value={num(overview.stats.sources)} detail="presse, actualités, boutiques" icon="globe" />
            <KpiTile label="En attente d'analyse" value={num(overview.stats.pending)} detail="Prochaine collecte à 06:00" icon="clock" />
          </section>

          <section className="card summary-card" aria-labelledby="summaryTitle">
            <div className="summary-head">
              <Icon name="sparkle" className="ai-icon" />
              <h2 className="summary-title" id="summaryTitle">Résumé de la semaine</h2>
              <span className="pill"><Icon name="sparkle" />Généré par IA · Claude</span>
              <span className="summary-meta">Semaine du {dayShort(current)}</span>
            </div>
            {overview.summary ? (
              <SummaryBody text={overview.summary.text} />
            ) : (
              <p className="summary-empty">Le résumé sera rédigé par l&apos;IA à la prochaine collecte.</p>
            )}
          </section>

          <section aria-labelledby="trendsTitle">
            <div className="section-head">
              <h2 className="section-title" id="trendsTitle">Tendances de la semaine</h2>
              <span className="section-note">Classées par momentum sur 4 semaines · les attributs en baisse sont listés plus bas</span>
            </div>
            <div className="trend-grid">
              {DIMENSIONS.map(dim => {
                const rows = overview.rising[dim] ?? [];
                return (
                  <article key={dim} className="card trend-card" aria-label={DIMENSION_TABS[dim]}>
                    <div className="trend-card-head">
                      <h3 className="trend-card-title">{DIMENSION_TABS[dim]}</h3>
                      <span className="pill">{rows.length} attribut{rows.length > 1 ? "s" : ""}</span>
                    </div>
                    <div className="trend-rows">
                      {rows.length ? rows.map(r => (
                        <TrendRowLink key={r.code} href={`/tendances/${dim}/${r.code}`} dimension={dim} row={r}
                                      spark={r.spark} status={r.status} momentum={r.momentum} tone={r} />
                      )) : <p className="section-note">Pas encore de mention cette semaine.</p>}
                    </div>
                    <div className="trend-card-foot">
                      <Link className="link-more" href={`/tendances?dim=${dim}`}>Voir tout<Icon name="arrowRight" /></Link>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>

          {shelf && shelf.stores.length > 0 && <ShelfGaps data={shelf} />}

          <section className="bottom-grid">
            <article className="card trend-card decline-card" aria-label="Tendances en baisse">
              <div className="trend-card-head">
                <h3 className="trend-card-title">En baisse</h3>
                <span className="pill">{overview.declining.length} attribut{overview.declining.length > 1 ? "s" : ""}</span>
              </div>
              <div className="trend-rows">
                {overview.declining.length ? overview.declining.map(r => (
                  <TrendRowLink key={`${r.dimension}-${r.code}`} href={`/tendances/${r.dimension}/${r.code}`} dimension={r.dimension}
                                row={r} spark={r.spark} status={r.status} momentum={r.momentum} tone={r} />
                )) : <p className="section-note">Aucun attribut en baisse cette semaine.</p>}
              </div>
            </article>

            <article className="card trend-card sources-card" aria-label="Dernières sources">
              <div className="trend-card-head">
                <h3 className="trend-card-title">Dernières sources</h3>
                <Link className="link-more" href="/sources">Toutes les sources<Icon name="arrowRight" /></Link>
              </div>
              <ul className="source-list">
                {latest.items.map(s => (
                  <li key={s.id} className="source-line">
                    <span className="source-name">{s.source}</span>
                    <LangPill lang={s.lang} />
                    <span className="source-quote">{s.quote ? `« ${s.quote} »` : s.title}</span>
                  </li>
                ))}
                {!latest.items.length && <li className="source-line"><span className="source-quote">Aucune source analysée pour l&apos;instant.</span></li>}
              </ul>
            </article>
          </section>
        </>
      )}
    </PageHeader>
  );
}
