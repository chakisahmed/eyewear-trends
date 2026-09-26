import { Suspense, type ReactNode } from "react";

import type { Meta } from "@/lib/types";

import { DemoBanner, ExportMenu, RefreshButton, WeekSelect } from "./HeaderActions";

/** Page title + the shared header actions (week, export, refresh) + the demo banner. */
export function PageHeader({ meta, title, subtitle, week, exportDimension, showWeek = true, children }: {
  meta: Meta;
  title: ReactNode;
  subtitle?: ReactNode;
  week: string | null;
  exportDimension?: string;
  showWeek?: boolean;
  children?: ReactNode;
}) {
  return (
    <>
      <header className="page-header">
        <div>
          <h1 className="page-title">{title}</h1>
          {subtitle && <p className="page-subtitle">{subtitle}</p>}
        </div>
        <div className="header-actions">
          {showWeek && (
            <Suspense fallback={null}>
              <WeekSelect weeks={meta.weeks} current={week} />
            </Suspense>
          )}
          <ExportMenu week={week} dimension={exportDimension} />
          <RefreshButton initiallyRunning={meta.running} />
        </div>
      </header>
      {meta.has_demo && <DemoBanner />}
      {children}
    </>
  );
}
