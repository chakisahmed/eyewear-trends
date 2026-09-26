import "server-only";

import { connection } from "next/server";

import type { Demand, Meta, Overview, Paged, SourceItem, Taxonomy, TrendDetail, Trends } from "./types";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

type Query = Record<string, string | number | undefined | null>;

/** Server-side GET against the FastAPI backend. Always fresh: this is a live dashboard. */
async function get<T>(path: string, query: Query = {}): Promise<T> {
  // Render at request time (this Next version has no `dynamic` segment config).
  await connection();
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  const qs = params.size ? `?${params}` : "";
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}${qs}`, { cache: "no-store" });
  } catch {
    throw new ApiError(503, "L'API est injoignable. Vérifiez que le backend est démarré.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  meta: () => get<Meta>("/api/meta"),
  taxonomy: () => get<Taxonomy>("/api/taxonomy"),
  overview: (week?: string) => get<Overview>("/api/overview", { week }),
  trends: (dimension: string, weeks: number, week?: string) => get<Trends>(`/api/trends/${dimension}`, { weeks, week }),
  trendDetail: (dimension: string, code: string, week?: string) =>
    get<TrendDetail>(`/api/trends/${dimension}/${encodeURIComponent(code)}`, { week }),
  demand: (dimension: string) => get<Demand>(`/api/demand/${dimension}`),
  sources: (q: Query) => get<Paged<SourceItem>>("/api/sources", q),
};
