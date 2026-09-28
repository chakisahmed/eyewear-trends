import Link from "next/link";

import { Icon } from "@/components/icons";
import { StatusBadge, Visual } from "@/components/ui";
import { num, pct } from "@/lib/format";
import { DIMENSION_TABS } from "@/lib/taxonomy";
import type { ProductType, RetailOverview, ShelfGap } from "@/lib/types";

const TYPE_LABEL: Record<ProductType, string> = { optical: "optique", sun: "solaire" };
const MAX_ROWS = 5;

function shelfDetail(g: ShelfGap): string {
  const shelf = `rayon ${TYPE_LABEL[g.product_type]}`;
  return (g.sku ? `${num(g.sku)} réf. · ${pct(g.share)} du ${shelf}` : `absent du ${shelf}`)
    + (g.clearance && g.markdown ? ` · déstockage +${num(g.markdown.relative_depth * 100)} pts` : "");
}

/** One row per attribute: the same trend can be a gap on both shelves (e.g. absent from optique and solaire). */
function groupByAttribute(gaps: ShelfGap[]): ShelfGap[][] {
  const groups = new Map<string, ShelfGap[]>();
  for (const g of gaps) {
    const key = `${g.dimension}/${g.code}`;
    groups.set(key, [...(groups.get(key) ?? []), g]);
  }
  return [...groups.values()];
}

function GapRow({ group }: { group: ShelfGap[] }) {
  const g = group[0];
  const allAbsent = group.length > 1 && group.every(x => !x.sku);
  const detail = allAbsent
    ? `absent des rayons ${group.map(x => TYPE_LABEL[x.product_type]).join(" et ")}`
    : group.map(shelfDetail).join(" · ");
  return (
    <Link className="trend-row gap-row" href={`/tendances/${g.dimension}/${g.code}`}>
      <Visual dimension={g.dimension} attr={g} />
      <span className="gap-text">
        <span className="trend-label">{g.label}</span>
        <span className="gap-detail">{detail}</span>
      </span>
      <StatusBadge status={g.status} momentum={g.momentum} />
    </Link>
  );
}

/** "Shelf vs. Signal" on the overview: where the press (leading) and Tunisian shelves (lagging) disagree.
 *  Gaps are computed per shelf (prescription vs sunglasses) by /api/retail/overview; no LLM involved. */
export function ShelfGaps({ data }: { data: RetailOverview }) {
  const skipped = (Object.keys(TYPE_LABEL) as ProductType[]).filter(t => data.skipped_dimensions[t].length > 0);
  const cards = [
    {
      key: "opportunities", title: "Opportunités", icon: "up" as const, gaps: groupByAttribute(data.opportunities),
      hint: `En hausse dans la presse, moins de ${pct(data.thresholds.opportunity_share)} du rayon`,
      empty: "Aucune tendance montante absente des rayons cette semaine.",
    },
    {
      key: "risks", title: "Risques de stock", icon: "down" as const, gaps: groupByAttribute(data.risks),
      hint: `En baisse dans la presse, ${pct(data.thresholds.risk_share)} du rayon ou plus, ou en déstockage`,
      empty: "Aucune tendance en recul encore très présente en rayon.",
    },
  ];

  return (
    <section className="shelf-gaps" aria-labelledby="gapsTitle">
      <div className="section-head">
        <h2 className="section-title" id="gapsTitle">Presse vs rayons tunisiens</h2>
        <span className="section-note">
          Signal international (presse) comparé aux références en boutique · optique {num(data.types.optical)} réf.,
          solaire {num(data.types.sun)} réf. · {data.stores.map(s => s.name).join(", ")}
        </span>
      </div>
      <div className="trend-grid">
        {cards.map(c => (
          <article key={c.key} className="card trend-card" aria-labelledby={`gap-${c.key}`}>
            <div className="trend-card-head">
              <h3 className="trend-card-title" id={`gap-${c.key}`}><Icon name={c.icon} className="gap-icon" />{c.title}</h3>
              <span className="pill">{c.gaps.length} écart{c.gaps.length > 1 ? "s" : ""}</span>
            </div>
            <p className="gap-hint">{c.hint}</p>
            <div className="trend-rows">
              {c.gaps.length
                ? c.gaps.slice(0, MAX_ROWS).map(group => <GapRow key={`${group[0].dimension}-${group[0].code}`} group={group} />)
                : <p className="section-note">{c.empty}</p>}
            </div>
            {c.gaps.length > MAX_ROWS && (
              <div className="trend-card-foot">
                <Link className="link-more" href="/rapport">+{c.gaps.length - MAX_ROWS} dans le rapport<Icon name="arrowRight" /></Link>
              </div>
            )}
          </article>
        ))}
      </div>
      {skipped.length > 0 && (
        <p className="gap-note">
          {skipped.map(t => `Rayon ${TYPE_LABEL[t]} : pas de comparaison pour ${data.skipped_dimensions[t].map(d => DIMENSION_TABS[d].toLowerCase()).join(", ")}`).join(" · ")}
          {" "}(trop peu de références renseignées, ou vocabulaire des boutiques non reconnu).
        </p>
      )}
    </section>
  );
}
