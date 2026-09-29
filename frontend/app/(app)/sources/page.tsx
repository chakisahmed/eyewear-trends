import Link from "next/link";
import { Suspense } from "react";

import { CatalogStatus } from "@/components/CatalogStatus";
import { Icon } from "@/components/icons";
import { UrlSelect } from "@/components/shell/Filters";
import { PageHeader } from "@/components/shell/PageHeader";
import { EmptyState, LangPill } from "@/components/ui";
import { api } from "@/lib/api";
import { swatchPaint } from "@/lib/chroma";
import { dayLong } from "@/lib/format";
import { DIMENSIONS, DIMENSION_TABS, KIND_LABELS, isDimension } from "@/lib/taxonomy";
import type { SourceKind } from "@/lib/types";

export const metadata = { title: "Sources" };

const PER_PAGE = 6;
const PERIODS = [{ value: "7", label: "7 derniers jours" }, { value: "30", label: "30 derniers jours" }, { value: "90", label: "3 derniers mois" }];
const KINDS = Object.keys(KIND_LABELS) as SourceKind[];
const DIM_SINGULAR: Record<string, string> = { shape: "Forme", color: "Couleur", material: "Matière", style: "Style" };

function one(v: string | string[] | undefined) {
  return typeof v === "string" ? v : undefined;
}

export default async function SourcesPage({ searchParams }: PageProps<"/sources">) {
  const q = await searchParams;
  const dim = isDimension(q.dim) ? q.dim : undefined;
  const code = dim ? one(q.code) : undefined;
  const lang = one(q.lang) === "fr" || one(q.lang) === "en" ? one(q.lang) : undefined;
  const kind = KINDS.includes(one(q.kind) as SourceKind) ? one(q.kind) : undefined;
  const days = PERIODS.some(p => p.value === one(q.days)) ? one(q.days)! : "30";
  const page = Math.max(1, Number(one(q.page)) || 1);

  const [meta, taxonomy, catalogs, result] = await Promise.all([
    api.meta(),
    api.taxonomy(),
    api.catalogs().catch(() => null),  // optional panel: the excerpts must not fail without it
    api.sources({ dimension: dim, code, lang, kind, days, limit: PER_PAGE, offset: (page - 1) * PER_PAGE }),
  ]);
  const pages = Math.max(1, Math.ceil(result.total / PER_PAGE));
  const filtered = Boolean(dim || lang || kind || days !== "30");
  const pageHref = (p: number) => {
    const next = new URLSearchParams(Object.entries({ dim, code, lang, kind, days: days === "30" ? undefined : days })
      .filter((e): e is [string, string] => Boolean(e[1])));
    if (p > 1) next.set("page", String(p));
    return `/sources${next.size ? `?${next}` : ""}`;
  };
  const reset = ["page"];

  return (
    <PageHeader meta={meta} week={null} showWeek={false} title="Sources"
                subtitle="Les extraits de presse, d'actualités, de boutiques et de réseaux sociaux derrière chaque tendance">
      <div className="screen-sources">
        {catalogs && catalogs.stores.length > 0 && <CatalogStatus data={catalogs} />}

        <section className="card filter-bar" aria-label="Filtres des sources">
          <Suspense fallback={null}>
            <div className="filter-grid">
              <div className="filter-field">
                <label htmlFor="fDimension">Dimension</label>
                <UrlSelect id="fDimension" param="dim" label="Dimension" current={dim ?? ""} reset={["code", ...reset]}
                           options={[{ value: "", label: "Toutes" }, ...DIMENSIONS.map(d => ({ value: d, label: DIMENSION_TABS[d] }))]} />
              </div>
              <div className="filter-field">
                <label htmlFor="fAttr">Attribut</label>
                <UrlSelect id="fAttr" param="code" label="Attribut" current={code ?? ""} reset={reset} disabled={!dim}
                           options={[{ value: "", label: "Tous" }, ...(dim ? taxonomy[dim].items.map(i => ({ value: i.code, label: i.label })) : [])]} />
              </div>
              <div className="filter-field">
                <label htmlFor="fLang">Langue</label>
                <UrlSelect id="fLang" param="lang" label="Langue" current={lang ?? ""} reset={reset}
                           options={[{ value: "", label: "Toutes" }, { value: "fr", label: "FR" }, { value: "en", label: "EN" }]} />
              </div>
              <div className="filter-field">
                <label htmlFor="fType">Type</label>
                <UrlSelect id="fType" param="kind" label="Type" current={kind ?? ""} reset={reset}
                           options={[{ value: "", label: "Tous" }, ...KINDS.map(k => ({ value: k, label: KIND_LABELS[k] }))]} />
              </div>
              <div className="filter-field">
                <label htmlFor="fPeriod">Période</label>
                <UrlSelect id="fPeriod" param="days" label="Période" current={days} reset={reset} options={PERIODS} />
              </div>
            </div>
          </Suspense>
        </section>

        <div className="results-head">
          <p className="result-count" aria-live="polite">
            <strong>{result.total} extrait{result.total > 1 ? "s" : ""}</strong>{filtered ? " correspondant aux filtres" : ""}
          </p>
          {filtered && <Link className="filter-reset" href="/sources">Réinitialiser les filtres</Link>}
        </div>

        {result.items.length ? (
          <div className="source-cards">
            {result.items.map(s => (
              <article key={s.id} className="card src-card">
                <header className="src-head">
                  <span className="src-name">{s.source}</span>
                  <span className="src-sep" aria-hidden="true">·</span>
                  {s.date && <time className="src-date" dateTime={s.date}>{dayLong(s.date)}</time>}
                  <LangPill lang={s.lang} />
                  <span className="pill">{KIND_LABELS[s.kind] ?? s.kind}</span>
                  {s.url.startsWith("http") && (
                    <a className="src-ext" href={s.url} target="_blank" rel="noopener noreferrer" aria-label={`Ouvrir la source ${s.source} (nouvel onglet)`}>
                      <Icon name="external" />
                    </a>
                  )}
                </header>
                <blockquote className="src-quote">{s.quote ? `« ${s.quote} »` : s.title}</blockquote>
                {s.summary && (
                  <p className="src-ai"><Icon name="sparkle" /><span><strong>Résumé IA :</strong> {s.summary}</span></p>
                )}
                <div className="src-chips">
                  {s.attributes.map(a => (
                    <Link key={`${a.dimension}-${a.code}`} className="attr-chip" href={`/tendances/${a.dimension}/${a.code}`} title={DIMENSION_TABS[a.dimension]}>
                      {a.dimension === "color" && (a.hex || a.multicolor) && <span className="chip-sw" style={{ ["--sw" as string]: swatchPaint(a) }} aria-hidden="true" />}
                      <span className="chip-dim">{DIM_SINGULAR[a.dimension]} ·</span> {a.label}
                    </Link>
                  ))}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="Aucun extrait ne correspond"
                      actions={filtered ? <Link className="btn btn-secondary" href="/sources">Réinitialiser les filtres</Link> : undefined}>
            {filtered ? "Élargissez la période ou retirez un filtre." : "Les extraits apparaîtront après la première collecte analysée."}
          </EmptyState>
        )}

        {pages > 1 && (
          <nav className="pagination" aria-label="Pagination des extraits">
            <p className="page-info">Page {page} sur {pages}</p>
            <div className="page-btns">
              {page > 1
                ? <Link className="page-btn" href={pageHref(page - 1)} aria-label="Page précédente"><Icon name="arrowLeft" /></Link>
                : <span className="page-btn" aria-disabled="true"><Icon name="arrowLeft" /></span>}
              {Array.from({ length: pages }, (_, i) => i + 1)
                .filter(p => p === 1 || p === pages || Math.abs(p - page) <= 2)
                .map((p, i, arr) => (
                  <span key={p} style={{ display: "contents" }}>
                    {i > 0 && p - arr[i - 1] > 1 && <span className="page-gap" aria-hidden="true">…</span>}
                    <Link className="page-btn" href={pageHref(p)} aria-label={`Page ${p}`} aria-current={p === page ? "page" : undefined}>{p}</Link>
                  </span>
                ))}
              {page < pages
                ? <Link className="page-btn" href={pageHref(page + 1)} aria-label="Page suivante"><Icon name="arrowRight" /></Link>
                : <span className="page-btn" aria-disabled="true"><Icon name="arrowRight" /></span>}
            </div>
          </nav>
        )}
      </div>
    </PageHeader>
  );
}
