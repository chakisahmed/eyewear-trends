import { Icon } from "@/components/icons";
import { dayShort, num, pct } from "@/lib/format";
import type { RetailPrice, TrendDetail } from "@/lib/types";

/** Price with the currency's usual decimals: TND has 3 but shelf prices are whole, so trim zeros. */
function money(v: number, currency: string | null): string {
  return `${num(v, Number.isInteger(v) ? 0 : 2)} ${currency === "EUR" ? "€" : currency ?? ""}`.trim();
}

function priceLine(p: RetailPrice): string {
  const range = p.min === p.max ? "" : ` (${money(p.min, p.currency)} – ${money(p.max, p.currency)})`;
  return `prix moyen ${money(p.avg, p.currency)}${range} · ${p.priced} prix`;
}

const COUNTRY_NAMES: Record<string, string> = { TN: "Tunisie", ES: "Espagne", FR: "France", IT: "Italie", PT: "Portugal" };

/** "Présence en boutique": what stores actually stock for this attribute (Shelf vs. Signal). */
export function RetailPresence({ d }: { d: TrendDetail }) {
  const count = d.retail_sku_count ?? 0;
  const stores = d.retail_store_count ?? 0;
  const bestsellers = d.retail_bestseller_count ?? 0;
  const types = d.retail_by_type ?? {};
  const sample = d.retail_sample ?? [];
  const label = d.label.toLowerCase();
  // Titled from the stores actually counted: the Tunisian retailers alone keep the "Marché Tunisien" lens; once a
  // brand catalog from elsewhere (Etnia Barcelona, Spain) is in the count, the title and note say so.
  const countries = d.retail_countries ?? [];
  const tunisianOnly = countries.every(c => c === "TN");
  const named = countries.map(c => COUNTRY_NAMES[c] ?? c).join(", ");

  return (
    <section className="retail" aria-labelledby="retailTitle">
      <div className="lens-head">
        <h2 className="lens-title" id="retailTitle">{tunisianOnly ? "Marché Tunisien (Boutiques)" : "Présence en boutique"}</h2>
        <span className="pill lens-tag">Indicateur retardé</span>
        {d.retail_updated_at && <span className="section-note lens-date">Relevé le {dayShort(d.retail_updated_at)}</span>}
        <p className="lens-note">
          {tunisianOnly
            ? "Disponibilité locale : références en rayon chez les enseignes tunisiennes suivies. Ce qui est déjà vendu ici."
            : `Références en rayon ou en catalogue chez les enseignes et marques suivies (${named}). Ce qui est déjà proposé à la vente.`}
        </p>
      </div>

      {count === 0 ? (
        <p className="card retail-empty">
          Aucune référence identifiée en boutique pour « {label} ». Les fiches produit des enseignes suivies
          ne mentionnent pas cet attribut (les noms de modèle ne décrivent souvent ni la forme ni la couleur).
        </p>
      ) : (
        <>
          <div className="card retail-summary">
            <p>
              <strong className="num">{num(count)}</strong> référence{count > 1 ? "s" : ""} en boutique
              · {num(stores)} enseigne{stores > 1 ? "s" : ""}
              {bestsellers > 0 && <> · dont <strong className="num">{num(bestsellers)}</strong> best-seller{bestsellers > 1 ? "s" : ""}</>}
            </p>
            {(d.retail_avg_price ?? []).map(p => <p key={p.currency} className="retail-price">{priceLine(p)}</p>)}
            {d.retail_markdown && (
              <p className="retail-markdown">
                {num(d.retail_markdown.discounted)}/{num(d.retail_markdown.compared)} réf. en promotion
                {d.retail_markdown.avg_depth != null && ` · remise moyenne ${pct(d.retail_markdown.avg_depth)}`}
                {` · ${d.retail_markdown.relative_depth >= 0 ? "+" : "−"}${num(Math.abs(d.retail_markdown.relative_depth) * 100)} pts vs la remise habituelle des enseignes`}
              </p>
            )}
            {(types.optical || types.sun) && (
              <p className="retail-types">
                {types.optical ? `Optique ${num(types.optical)}` : null}
                {types.optical && types.sun ? " · " : null}
                {types.sun ? `Solaire ${num(types.sun)}` : null}
                {(types.optical ?? 0) + (types.sun ?? 0) > count ? " (certaines références sont classées dans les deux)" : null}
              </p>
            )}
          </div>

          <ul className="retail-grid" aria-label={`Exemples de références « ${label} » en boutique`}>
            {sample.map(p => (
              <li key={p.url} className="card retail-card">
                <a href={p.url} target="_blank" rel="noopener noreferrer" aria-label={`${p.name}, ${p.store} (nouvel onglet)`}>
                  <span className="retail-img">
                    {p.image_url
                      // eslint-disable-next-line @next/next/no-img-element -- store images from arbitrary hosts, shown as-is
                      ? <img src={p.image_url} alt="" width={160} height={160} loading="lazy" referrerPolicy="no-referrer" />
                      : <Icon name="sources" />}
                  </span>
                  <span className="retail-name">{p.name}</span>
                  <span className="retail-meta">{p.brand && p.brand !== p.store ? `${p.brand} · ${p.store}` : p.store}</span>
                  <span className="retail-row">
                    <span className="retail-amount num">{p.price != null ? money(p.price, p.currency) : "Prix non affiché"}</span>
                    {p.is_bestseller && <span className="pill retail-bestseller"><Icon name="up" />Best-seller</span>}
                    {p.out_of_stock && <span className="pill retail-soldout"><Icon name="alert" />Épuisé</span>}
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
