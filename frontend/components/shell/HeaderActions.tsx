"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { Icon } from "@/components/icons";
import { dayShort } from "@/lib/format";
import { DIMENSIONS, DIMENSION_TABS } from "@/lib/taxonomy";
import type { JobRun } from "@/lib/types";

/** Monday of the current week, "YYYY-MM-DD" (local time), to flag the week still in progress. */
function currentMonday(now = new Date()): string {
  const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - ((now.getDay() + 6) % 7));
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Week selector: rewrites ?week= on the current page, keeping the other filters. The default page week is the
 *  last complete week (chosen by the API), so the choice is always written to the URL, even for the newest week. */
export function WeekSelect({ weeks, current }: { weeks: string[]; current: string | null }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  if (!weeks.length) return null;
  const inProgress = currentMonday();
  return (
    <label className="sr-only-label">
      <span className="sr-only">Semaine affichée</span>
      <select className="select week-select" value={current ?? weeks[0]}
              onChange={e => {
                const next = new URLSearchParams(params.toString());
                next.set("week", e.target.value);
                router.push(`${pathname}?${next}`);
              }}>
        {weeks.map(w => (
          <option key={w} value={w}>Semaine du {dayShort(w)}{w === inProgress ? " (en cours)" : ""}</option>
        ))}
      </select>
    </label>
  );
}

export function ExportMenu({ week, dimension }: { week: string | null; dimension?: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("click", close);
    document.addEventListener("keydown", close);
    return () => { document.removeEventListener("click", close); document.removeEventListener("keydown", close); };
  }, [open]);
  const q = week ? `?week=${week}` : "";
  const dims = dimension ? [dimension] : DIMENSIONS;
  return (
    <div className="menu-wrap" ref={ref}>
      <button className="btn btn-secondary" type="button" aria-haspopup="true" aria-expanded={open} onClick={() => setOpen(!open)}>
        <Icon name="download" />
        Exporter
      </button>
      <div className={`menu${open ? " open" : ""}`} role="menu" aria-label="Options d'export">
        <p className="menu-label">Tableau (CSV)</p>
        {dims.map(d => (
          <a key={d} role="menuitem" href={`/api/export/${d}.csv${q}`} download onClick={() => setOpen(false)}>
            <Icon name="fileTable" />
            {DIMENSION_TABS[d as keyof typeof DIMENSION_TABS]}
          </a>
        ))}
        <div className="menu-sep" />
        <a role="menuitem" href={`/rapport${q}`} target="_blank" rel="noopener" onClick={() => setOpen(false)}>
          <Icon name="fileReport" />
          Rapport PDF
        </a>
      </div>
    </div>
  );
}

type Progress = JobRun["progress"];
type RunState = { running: boolean; message: string | null; failed: boolean; progress: Progress | null };

/** "Étape 4/6 · Analyse IA · 12/40" — or "…" while a step has no countable items. */
function describe(p: Progress | null): string {
  if (!p?.label) return "Démarrage de la collecte…";
  const counted = p.total != null && p.total > 0 ? ` · ${p.done ?? 0}/${p.total}` : "…";
  return `Étape ${p.index ?? "?"}/${p.count} · ${p.label}${counted}`;
}

/** Starts a collection run, then polls its status (showing the current step) and refreshes the page when it ends. */
export function RefreshButton({ initiallyRunning }: { initiallyRunning: boolean }) {
  const router = useRouter();
  const [state, setState] = useState<RunState>({ running: initiallyRunning, message: null, failed: false, progress: null });

  const poll = useCallback(async () => {
    for (;;) {
      try {
        const s = await (await fetch("/api/jobs/status", { cache: "no-store" })).json();
        if (s.running) {
          const current: JobRun | null = s.current;
          setState(prev => ({ ...prev, running: true, progress: current?.progress ?? null }));
          await new Promise(r => setTimeout(r, 3000));
          continue;
        }
        const last: JobRun | null = s.last;
        const failed = last?.status === "failed";
        setState({ running: false, failed, progress: null, message: failed ? `La collecte a échoué : ${last?.error ?? "erreur inconnue"}` : "Collecte terminée, données mises à jour." });
        router.refresh();
        return;
      } catch {
        setState({ running: false, failed: true, progress: null, message: "Impossible de joindre l'API pendant la collecte." });
        return;
      }
    }
  }, [router]);

  // A run was already going when the page loaded: follow it (started from a timer callback).
  useEffect(() => {
    if (!initiallyRunning) return;
    const t = setTimeout(() => void poll(), 0);
    return () => clearTimeout(t);
  }, [initiallyRunning, poll]);

  async function start() {
    setState({ running: true, message: null, failed: false, progress: null });
    const res = await fetch("/api/jobs/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    if (res.status === 202 || res.status === 409) {
      void poll(); // 409 = a run is already going: follow it
    } else {
      setState({ running: false, failed: true, progress: null, message: `Impossible de lancer la collecte (HTTP ${res.status}).` });
    }
  }

  const p = state.progress;
  const pct = p?.total ? Math.round(100 * (p.done ?? 0) / p.total) : null;
  return (
    <>
      <button className={`btn btn-primary${state.running ? " is-loading" : ""}`} type="button" disabled={state.running} onClick={start}>
        <span className="btn-icon"><Icon name="refresh" /></span>
        <span className="btn-spinner" aria-hidden="true" />
        <span className="btn-label">{state.running ? "Collecte en cours…" : "Actualiser les données"}</span>
      </button>
      {state.running ? (
        <p className="run-note run-progress" role="status" aria-live="polite">
          <span>{describe(p)}</span>
          {pct != null && (
            <span className="run-bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-label="Avancement de l'étape">
              <span style={{ width: `${pct}%` }} />
            </span>
          )}
        </p>
      ) : state.message && (
        <p className={`run-note${state.failed ? " failed" : ""}`} role="status">{state.message}</p>
      )}
    </>
  );
}

/** Demo-data banner; "Retirer la démo" deletes the demo rows through the API. */
export function DemoBanner() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  return (
    <div className="demo-banner" role="status">
      <Icon name="sparkle" />
      <p>
        Données de démonstration : les tendances affichées sont fictives en attendant la première collecte.{" "}
        <a href="#" aria-disabled={busy} onClick={async e => {
          e.preventDefault();
          if (busy) return;
          setBusy(true);
          await fetch("/api/demo", { method: "DELETE" });
          router.refresh();
        }}>{busy ? "Suppression…" : "Retirer la démo"}</a>
      </p>
    </div>
  );
}

/** Empty-state action: load the synthetic demo data set. */
export function LoadDemoButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  return (
    <button className="btn btn-secondary" type="button" disabled={busy} onClick={async () => {
      setBusy(true);
      await fetch("/api/demo", { method: "POST" });
      router.refresh();
    }}>
      <Icon name="sparkle" />
      {busy ? "Chargement…" : "Charger la démo"}
    </button>
  );
}
