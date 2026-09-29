import { Suspense } from "react";

import { MiniDemandCard } from "@/components/charts/MiniDemand";
import { Icon } from "@/components/icons";
import { UrlSelect, UrlTabs } from "@/components/shell/Filters";
import { PageHeader } from "@/components/shell/PageHeader";
import { EmptyState, StatusBadge, Visual } from "@/components/ui";
import { api } from "@/lib/api";
import { DIMENSIONS, DIMENSION_TABS, isDimension } from "@/lib/taxonomy";

export const metadata = { title: "Demande" };

const PERIODS = [8, 12, 26];

export default async function DemandPage({ searchParams }: PageProps<"/demande">) {
  const q = await searchParams;
  const dim = isDimension(q.dim) ? q.dim : "shape";
  const weeks = PERIODS.includes(Number(q.weeks)) ? Number(q.weeks) : 12;
  const [meta, demand, trends] = await Promise.all([api.meta(), api.demand(dim), api.trends(dim, 12)]);
  const trendOf = Object.fromEntries(trends.series.map(s => [s.code, s]));
  const geoLabel = meta.market_geo === "FR" ? "France" : meta.market_geo;
  const from = Math.max(0, demand.weeks.length - weeks);

  // Attributes with search data, plus press trends with enough data but no search volume (shown with a
  // "too low" note rather than hidden), sorted by the attribute's momentum. Dimensions not tracked on
  // Google Trends at all (no rows, e.g. styles) keep the empty state instead of "too low" cards.
  const withSearch = new Set(demand.series.map(s => s.code));
  const noSearch = demand.weeks.map(() => null);
  const pressOnly = demand.series.length
    ? trends.series.filter(t => !withSearch.has(t.code) && t.status !== "faible").map(t => ({ ...t, fr: noSearch, world: noSearch }))
    : [];
  const cards = [...demand.series, ...pressOnly].sort((a, b) => (trendOf[b.code]?.momentum ?? -9) - (trendOf[a.code]?.momentum ?? -9));

  return (
    <PageHeader meta={meta} week={trends.week} exportDimension={dim} showWeek={false} title="Demande"
                subtitle={`Intérêt de recherche Google · ${DIMENSION_TABS[dim].toLowerCase()} · ${geoLabel} et Monde`}>
      <div className="screen-demand">
        <div className="filter-bar">
          <Suspense fallback={null}>
            <UrlTabs param="dim" label="Dimension" current={dim} options={DIMENSIONS.map(d => ({ value: d, label: DIMENSION_TABS[d] }))} />
            <UrlSelect param="weeks" label="Période" current={String(weeks)}
                       options={PERIODS.map(p => ({ value: String(p), label: `${p} semaines` }))} />
          </Suspense>
        </div>

        {cards.length ? (
          <section className="demand-grid" aria-label={`Intérêt de recherche par attribut : ${DIMENSION_TABS[dim].toLowerCase()}`}>
            {cards.map(s => {
              const t = trendOf[s.code];
              return (
                <MiniDemandCard key={s.code} label={s.label} geoLabel={geoLabel} hex={dim === "color" ? s.hex : null}
                                multicolor={dim === "color" && !!s.multicolor}
                                weeks={demand.weeks.slice(from)} fr={s.fr.slice(from)} world={s.world.slice(from)}
                                head={<>
                                  <Visual dimension={dim} attr={s} />
                                  <h2 className="demand-label">{s.label}</h2>
                                  {t && (
                                    <span className="trend-tag" title="Statut global : mentions presse + recherche">
                                      <span className="trend-tag-label">Tendance</span>
                                      <StatusBadge status={t.status} momentum={t.momentum} tone={t} />
                                    </span>
                                  )}
                                </>} />
              );
            })}
          </section>
        ) : (
          <EmptyState title="Pas encore de données de recherche">
            L&apos;intérêt Google Trends est collecté avec les autres sources lors de chaque actualisation.
          </EmptyState>
        )}

        <aside className="card note-card" role="note">
          <Icon name="alert" />
          <p>
            <strong>Comment lire ces courbes :</strong> l&apos;intérêt Google Trends est relatif (0–100) : 100 = pic de
            popularité du mot-clé sur la période. Les mots-clés sont suivis en français et en anglais. Le badge
            « Tendance » est le statut global (mentions presse + recherche) ; la courbe ne montre que la recherche.
          </p>
        </aside>
      </div>
    </PageHeader>
  );
}
