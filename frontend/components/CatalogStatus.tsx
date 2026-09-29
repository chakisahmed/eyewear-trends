import { Icon } from "@/components/icons";
import { swatchPaint } from "@/lib/chroma";
import { ago, num, pct } from "@/lib/format";
import { DIMENSION_TABS } from "@/lib/taxonomy";
import type { Catalogs } from "@/lib/types";

const COUNTRY_NAMES: Record<string, string> = { TN: "Tunisie", ES: "Espagne", FR: "France", IT: "Italie", PT: "Portugal", US: "États-Unis", GB: "Royaume-Uni" };
const DIM_SINGULAR: Record<string, string> = { shape: "Forme", color: "Couleur", material: "Matière", style: "Style" };

/** "Catalogues et boutiques suivis": can the store data be trusted (state of each store's crawls), and what changed in it
 *  (new and retired frames over 30 days, and what creator brands added). Read from the crawl log by /api/catalogs. */
export function CatalogStatus({ data }: { data: Catalogs }) {
  const stores = data.stores;
  const attention = stores.filter(s => s.status === "late" || s.status === "incomplete" || s.status === "failed" || s.note);
  const enough = data.new_total >= data.min_for_shares;

  return (
    <section className="card catalogs" aria-labelledby="catalogsTitle">
      <div className="section-head">
        <h2 className="section-title" id="catalogsTitle">Catalogues et boutiques suivis</h2>
        <span className="section-note">
          {data.has_history
            ? `Nouveautés et retraits : ${data.since_days} derniers jours, depuis la première collecte complète de chaque enseigne`
            : "Historique en cours de constitution"}
        </span>
      </div>
      {!data.has_history && (
        <p className="cat-empty">
          Les nouveautés et les retraits apparaîtront après la première collecte complète de chaque enseigne
          (<code>crawl-stores</code>). Les collectes faites à la main avant ce suivi n&apos;ont pas de date d&apos;arrivée fiable.
        </p>
      )}
      <div className="table-scroll">
        <table className="data-table">
          <caption className="sr-only">État de la collecte de chaque boutique ou catalogue suivi</caption>
          <thead>
            <tr>
              <th scope="col">Enseigne</th>
              <th scope="col" className="numcol">Réf. actives</th>
              <th scope="col" className="numcol">Nouveautés</th>
              <th scope="col" className="numcol">Retirées</th>
              <th scope="col">Dernière collecte complète</th>
              <th scope="col">État</th>
            </tr>
          </thead>
          <tbody>
            {stores.map(s => (
              <tr key={s.domain}>
                <th scope="row">
                  <span className="cat-store">{s.name}</span>
                  {s.country && <span className="cat-country">{COUNTRY_NAMES[s.country] ?? s.country}{s.creator ? " · marque" : ""}</span>}
                </th>
                <td className="numcol">{s.products ? num(s.products) : "–"}</td>
                <td className="numcol">{s.has_history ? num(s.new) : "–"}</td>
                <td className="numcol">{s.has_history ? num(s.retired) : "–"}</td>
                <td>{s.last_ok_at ? ago(s.last_ok_at) : "–"}</td>
                <td>
                  <span className="cat-state" data-status={s.status}>
                    <span className="cat-dot" aria-hidden="true" />{s.status_label}
                  </span>
                  {s.detail && <span className="cat-detail">{s.detail}</span>}
                  {s.note && <span className="cat-detail">Suppressions ignorées : {s.note}</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {attention.length > 0 && (
        <p className="cat-new">
          <Icon name="alert" className="gap-icon" />
          {attention.map(s => s.name).join(", ")} : la collecte demande un coup d&apos;œil (voir le journal, ou lancer{" "}
          <code>python -m app.cli crawl-store {attention[0].domain}</code>).
        </p>
      )}
      {data.has_history && (
        <p className="cat-new">
          {data.new_total > 0 ? (
            <>
              <strong>{num(data.new_total)} nouveauté{data.new_total > 1 ? "s" : ""}</strong> chez les marques créatrices
              ({num(data.retired_total)} retirée{data.retired_total > 1 ? "s" : ""}).{" "}
              {enough
                ? data.top.map((t, i) => (
                    <span key={`${t.dimension}-${t.code}`}>
                      {i > 0 && " · "}
                      {t.dimension === "color" && (t.hex || t.multicolor) && (
                        <span className="swatch" style={{ background: swatchPaint(t), width: 11, height: 11, display: "inline-block", verticalAlign: "-1px", marginRight: 5 }} aria-hidden="true" />
                      )}
                      <span title={DIMENSION_TABS[t.dimension]}>{DIM_SINGULAR[t.dimension]} {t.label}</span> {num(t.new)}
                      {t.share_new != null && t.share_catalog != null && <span className="retail-since"> ({pct(t.share_new)} des nouveautés, {pct(t.share_catalog)} du catalogue)</span>}
                    </span>
                  ))
                : `Trop peu pour parler de tendance (moins de ${data.min_for_shares}) : les parts ne sont pas calculées.`}
            </>
          ) : (
            "Aucune nouveauté chez les marques créatrices sur la période."
          )}
        </p>
      )}
    </section>
  );
}
