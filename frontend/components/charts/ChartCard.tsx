"use client";

import { useState, type ReactNode } from "react";

/** Card with a "Graphique / Vue tableau" toggle: every chart has an accessible table alternative. */
export function ChartCard({ title, subtitle, graph, table, note, className = "", titleId }: {
  title: ReactNode;
  subtitle?: ReactNode;
  graph: ReactNode;
  table: ReactNode;
  note?: ReactNode;
  className?: string;
  titleId?: string;
}) {
  const [asTable, setAsTable] = useState(false);
  return (
    <article className={`card ${className}`} aria-labelledby={titleId}>
      <div className="card-head">
        <div>
          <h2 className="card-title" id={titleId}>{title}</h2>
          {subtitle && <p className="card-sub">{subtitle}</p>}
        </div>
        <div className="seg" role="group" aria-label="Mode d'affichage">
          <button type="button" className="seg-btn" aria-pressed={!asTable} onClick={() => setAsTable(false)}>Graphique</button>
          <button type="button" className="seg-btn" aria-pressed={asTable} onClick={() => setAsTable(true)}>Vue tableau</button>
        </div>
      </div>
      {asTable ? table : graph}
      {note && <p className="card-note">{note}</p>}
    </article>
  );
}
