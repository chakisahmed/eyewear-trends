import { Icon } from "@/components/icons";
import { swatchPaint } from "@/lib/chroma";
import { num, pct } from "@/lib/format";
import type { TrendDetail } from "@/lib/types";

/** "Associations fréquentes": the colours this one is laminated with in the catalogs we follow (colour pages only).
 *  Counted in frames (models); a coral edge and the best-seller pill mark pairings that include best-selling frames. */
export function FrequentPairings({ d }: { d: TrendDetail }) {
  const p = d.pairings;
  if (!p || !p.partners.length) return null;
  const label = d.label.toLowerCase();

  return (
    <section className="pairings" aria-labelledby="pairingsTitle">
      <div className="section-head">
        <h2 className="section-title" id="pairingsTitle">Associations fréquentes</h2>
        <span className="section-note">
          {num(p.frames)} modèle{p.frames > 1 ? "s" : ""} · {p.stores.join(", ")}
          {p.bestsellers > 0 && <> · dont {num(p.bestsellers)} best-seller{p.bestsellers > 1 ? "s" : ""}</>}
        </span>
      </div>
      <p className="pairings-intro">
        Couleurs le plus souvent associées au {label} dans les acétates multicouches : un modèle compte une fois par
        association, même s&apos;il existe en plusieurs coloris. Le trait corail signale les associations qui comptent des best-sellers.
      </p>
      <div className="card pair-card">
        <ul className="pair-list" aria-label={`Associations les plus fréquentes avec ${label}`}>
          {p.partners.map(x => (
            <li key={x.code} className={x.bestsellers > 0 ? "pair-row pair-best" : "pair-row"}>
              <span className="pair-name">
                <span className="pair-swatches" aria-hidden="true">
                  <span className="swatch" style={{ background: swatchPaint(d) }} />
                  <span className="swatch" style={{ background: swatchPaint(x) }} />
                </span>
                <span title={`${d.label} + ${x.label}`}>{d.label} + {x.label}</span>
              </span>
              <span className="pair-track" role="img" aria-label={`${pct(x.frames / p.frames)} des modèles`}>
                <span className="pair-fill" style={{ width: `${(100 * x.frames / p.frames).toFixed(1)}%`, background: swatchPaint(x) }} />
              </span>
              <span className="pair-val num">{num(x.frames)} <small>modèle{x.frames > 1 ? "s" : ""}</small></span>
              {x.bestsellers > 0 && (
                <span className="pair-flag">
                  <span className="pill retail-bestseller"><Icon name="up" />{num(x.bestsellers)} best-seller{x.bestsellers > 1 ? "s" : ""} · {pct(x.bestsellers / x.frames)}</span>
                  {x.examples.length > 0 && (
                    <span>
                      ex.{" "}
                      {x.examples.map((e, i) => (
                        <span key={e.url}>
                          {i > 0 && ", "}
                          <a href={e.url} target="_blank" rel="noopener noreferrer" aria-label={`${e.name}, ${e.store} (nouvel onglet)`}>{e.name}</a>
                        </span>
                      ))}
                    </span>
                  )}
                </span>
              )}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
