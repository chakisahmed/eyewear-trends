import Link from "next/link";

import { Icon } from "@/components/icons";
import { PrintButton } from "@/components/PrintButton";
import { SummaryBody } from "@/components/Summary";
import { LangPill, Sparkline, StatusBadge, Visual } from "@/components/ui";
import { api } from "@/lib/api";
import { dayLong, dayShort, num, pct, stamp } from "@/lib/format";
import { DIMENSIONS, DIMENSION_TABS, STATUS } from "@/lib/taxonomy";

export const metadata = { title: "Rapport tendances lunettes" };

/** One-page A4 report for buying meetings (outside the app shell; always light). */
export default async function ReportPage({ searchParams }: PageProps<"/rapport">) {
  const { week: weekParam } = await searchParams;
  const week = typeof weekParam === "string" ? weekParam : undefined;
  const [meta, overview, quotes] = await Promise.all([api.meta(), api.overview(week), api.sources({ limit: 3 })]);
  const current = overview.week;
  const rising = DIMENSIONS.flatMap(d => overview.rising[d] ?? []).filter(r => r.status === "en_hausse").length;
  const reasonText = (r: (typeof overview.declining)[number]) =>
    r.decline_reason === "tonalite" && r.decline_share != null
      ? `${pct(r.decline_share)} d'avis « en recul »`
      : `Volume en baisse${r.decline_share ? ` · ${pct(r.decline_share)} d'avis « en recul »` : ""}`;

  return (
    <div className="screen-report">
      <nav className="report-toolbar" aria-label="Actions du rapport">
        <Link href="/">← Retour au tableau de bord</Link>
        <span className="hint">Format A4 · choisissez « Enregistrer au format PDF » dans la fenêtre d&apos;impression</span>
        <PrintButton />
      </nav>

      <main className="sheet">
        <header className="r-head">
          <div className="r-brand">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/brand/noe-noah-logo-coral.png" alt="Noé & Noah" width={70} height={37} />
            <div>
              <h1 className="r-title">Rapport tendances lunettes</h1>
              <p className="r-sub">
                {current ? `Semaine du ${dayLong(current)}` : "Aucune semaine analysée"} · presse, actualités, boutiques et réseaux sociaux (FR + EN)
              </p>
            </div>
          </div>
          <div className="r-meta">
            {meta.last_success?.finished_at ? <>Données du {stamp(meta.last_success.finished_at)}<br /></> : null}
            Équipe achats &amp; merchandising<br />
            {meta.has_demo && <span className="pill">Données de démonstration</span>}
          </div>
        </header>

        <section className="r-kpis" aria-label="Chiffres clés">
          <div className="r-kpi"><div className="r-kpi-label">Articles analysés</div><div className="r-kpi-value">{num(overview.stats.documents)}</div><div className="r-kpi-detail">avec tendances détectées</div></div>
          <div className="r-kpi"><div className="r-kpi-label">Mentions d&apos;attributs</div><div className="r-kpi-value">{num(overview.stats.mentions)}</div><div className="r-kpi-detail">formes, couleurs, matières, styles</div></div>
          <div className="r-kpi"><div className="r-kpi-label">Sources suivies</div><div className="r-kpi-value">{num(overview.stats.sources)}</div><div className="r-kpi-detail">FR + EN</div></div>
          <div className="r-kpi"><div className="r-kpi-label">Signaux forts</div><div className="r-kpi-value">{rising}</div><div className="r-kpi-detail">en hausse · {overview.declining.length} en baisse</div></div>
        </section>

        <section className="r-summary" aria-labelledby="sumTitle">
          <h2 className="r-section-title" id="sumTitle">
            <Icon name="sparkle" />Résumé de la semaine
            <span className="note">Généré par IA · Claude</span>
          </h2>
          {overview.summary ? <SummaryBody text={overview.summary.text} /> : <p>Le résumé sera rédigé par l&apos;IA à la prochaine collecte.</p>}
        </section>

        <section aria-labelledby="topTitle">
          <h2 className="r-section-title" id="topTitle">
            <Icon name="trends" />Tendances de la semaine
            <span className="note">Classées par momentum sur 4 semaines · courbes : 8 dernières semaines</span>
          </h2>
          <div className="r-grid">
            {DIMENSIONS.map(dim => (
              <div key={dim} className="r-dim">
                <h3>{DIMENSION_TABS[dim]}</h3>
                <table className="r-table">
                  <tbody>
                    {(overview.rising[dim] ?? []).slice(0, 4).map(r => (
                      <tr key={r.code}>
                        <td className="vis"><Visual dimension={dim} attr={r} /></td>
                        <td className="name">{r.label}</td>
                        <td className="spark-cell"><Sparkline values={r.spark} label={`${r.label} : ${STATUS[r.status].label.toLowerCase()}`} /></td>
                        <td className="mom"><StatusBadge status={r.status} momentum={r.momentum} tone={r} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </section>

        <div className="r-bottom">
          <section aria-labelledby="downTitle">
            <h2 className="r-section-title" id="downTitle"><Icon name="down" />En baisse</h2>
            <table className="r-table" aria-labelledby="downTitle">
              <tbody>
                {overview.declining.slice(0, 4).map(r => (
                  <tr key={`${r.dimension}-${r.code}`}>
                    <td className="vis"><Visual dimension={r.dimension} attr={r} /></td>
                    <td className="name">{r.label}<span className="reason">{reasonText(r)}</span></td>
                    <td className="spark-cell"><Sparkline values={r.spark} label={`${r.label} : en baisse`} /></td>
                    <td className="mom"><StatusBadge status={r.status} momentum={r.momentum} /></td>
                  </tr>
                ))}
                {!overview.declining.length && <tr><td className="name">Aucun attribut en baisse cette semaine.</td></tr>}
              </tbody>
            </table>
          </section>

          <section aria-labelledby="quoteTitle">
            <h2 className="r-section-title" id="quoteTitle"><Icon name="sources" />Citations clés</h2>
            <div className="r-quotes">
              {quotes.items.map(s => (
                <blockquote key={s.id} className="r-quote">
                  <p>{s.quote ? `« ${s.quote} »` : s.title}</p>
                  <div className="src">
                    <strong>{s.source}</strong>{s.date ? ` · ${dayShort(s.date)}` : ""} · <LangPill lang={s.lang} /> · {s.attributes.slice(0, 2).map(a => a.label).join(", ")}
                  </div>
                </blockquote>
              ))}
            </div>
          </section>
        </div>

        <footer className="r-foot">
          <span className="method">Momentum : mentions pondérées vs moyenne des 4 semaines précédentes, avec l&apos;intérêt Google Trends. « En baisse » : volume −25&#8239;% ou majorité d&apos;avis « en recul ».</span>
          <span>Généré automatiquement · Noé &amp; Noah · page 1/1</span>
        </footer>
      </main>
    </div>
  );
}
