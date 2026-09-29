// Shapes of the FastAPI responses (backend/app/api/main.py).

export type Dimension = "shape" | "color" | "material" | "style";
/** "faible" = too few mentions over 4 weeks for any trend claim. */
export type Status = "en_hausse" | "au_pic" | "stable" | "en_baisse" | "faible";
export type Stance = "rising" | "neutral" | "declining";
export type SourceKind = "press" | "news" | "store" | "social";

export interface Attribute {
  code: string;
  label: string;
  hex: string | null;
  /** Color family with no single hue ("Multicolore"): drawn as a spectrum, hex is only a fallback. */
  multicolor?: boolean;
}

export interface Tone {
  tone: number | null;
  decline_share: number | null;
  decline_reason: "volume" | "tonalite" | null;
}

export interface TrendRow extends Attribute, Tone {
  dimension: Dimension;
  mentions: number;
  momentum: number;
  status: Status;
  spark: number[];
}

export interface Overview {
  week: string | null;
  stats: { documents: number; mentions: number; sources: number; pending: number };
  has_demo: boolean;
  dimension_labels: Record<Dimension, string>;
  rising: Partial<Record<Dimension, TrendRow[]>>;
  declining: TrendRow[];
  summary: { text: string; model: string } | null;
}

export interface TrendSeries extends Attribute, Tone {
  mentions: number[];
  search: (number | null)[];
  momentum: number;
  status: Status;
  share: number;
}

export interface Trends {
  week: string | null;
  weeks: string[];
  series: TrendSeries[];
}

export interface MentionRow extends Attribute {
  dimension: Dimension;
  stance: Stance;
  evidence: string;
  date: string;
  title: string;
  url: string;
  summary: string | null;
  lang: string;
  source: string;
  kind: SourceKind;
  is_demo: boolean;
}

export interface TrendDetail extends Attribute, Tone {
  dimension: Dimension;
  dimension_label: string;
  week: string | null;
  weeks: string[];
  mentions: number[];
  momentum: number;
  status: Status;
  rising_streak: number;
  stats: { this_week: number; avg_4w: number | null; share: number; search_fr: number | null };
  search: { fr: (number | null)[]; world: (number | null)[] };
  stance: Record<Stance, number>;
  brands: { name: string; count: number }[];
  evidence: MentionRow[];
  // "Présence en boutique": store products tagged with this attribute (rule-based, no LLM)
  retail_sku_count?: number;
  retail_store_count?: number;
  /** Tagged products the store itself flags as best-sellers (frame level; stores that publish it, e.g. Etnia). */
  retail_bestseller_count?: number;
  /** ISO country codes of the stores counted (Tunisian retailers, a Spanish brand catalog…). */
  retail_countries?: string[];
  retail_avg_price?: RetailPrice[];
  retail_by_type?: Partial<Record<"optical" | "sun", number>>;
  retail_sample?: RetailProduct[];
  retail_updated_at?: string | null;
  retail_markdown?: Markdown | null;
  /** Colour pages only: what this colour is laminated with in the tracked catalogs; null when no frame shows it. */
  pairings?: Pairings | null;
}

export interface PairingExample {
  name: string;
  url: string;
  store: string;
}

/** Frames = distinct catalog models (a frame with several colourways counts once). Best-sellers are the store's own flag. */
export interface PairingCounts {
  frames: number;
  bestsellers: number;
  /** Up to two best-selling frames, by the store's listing order. */
  examples: PairingExample[];
}

export interface Pairings extends PairingCounts {
  stores: string[];
  partners: (PairingCounts & Attribute)[];
}

/** Discount signal: markdown vs each store's usual sale (stores without list prices are excluded). */
export interface Markdown {
  compared: number;
  discounted: number;
  share_discounted: number;
  avg_depth: number | null;
  relative_depth: number;
}

export interface RetailPrice {
  currency: string;
  avg: number;
  min: number;
  max: number;
  priced: number;
}

export interface RetailProduct {
  name: string;
  brand: string | null;
  price: number | null;
  currency: string | null;
  image_url: string | null;
  url: string;
  store: string;
  out_of_stock: boolean;
  is_bestseller?: boolean;
}

export interface Demand {
  weeks: string[];
  geo: string;
  series: (Attribute & { fr: (number | null)[]; world: (number | null)[] })[];
}

export interface SourceItem {
  id: number;
  url: string;
  title: string;
  source: string;
  kind: SourceKind;
  lang: string;
  date: string | null;
  quote: string | null;
  summary: string | null;
  attributes: (Attribute & { dimension: Dimension; stance: Stance })[];
  is_demo: boolean;
}

export interface Paged<T> {
  total: number;
  limit: number;
  offset: number;
  items: T[];
}

export interface JobRun {
  id: number;
  status: "running" | "success" | "failed";
  trigger: string;
  steps: string[];
  started_at: string;
  finished_at: string | null;
  report: Record<string, unknown> | null;
  error: string | null;
  progress: {
    step: string | null;
    label: string | null;
    index: number | null;
    count: number;
    done: number | null;
    total: number | null;
  };
}

export interface Meta {
  has_demo: boolean;
  weeks: string[];
  running: boolean;
  last_success: JobRun | null;
  market_geo: string;
}

export type Taxonomy = Record<Dimension, { label: string; items: Attribute[] }>;

/** Tunisian shelf vs press signal (report): computed gaps, no LLM. */
export interface ShelfGap extends Attribute {
  dimension: Dimension;
  status: Status;
  momentum: number;
  sku: number;
  share: number;
  avg_price: Record<string, number>;
  markdown: Markdown | null;
  clearance: boolean;
  product_type: ProductType;
}

export type ProductType = "optical" | "sun";

export interface RetailOverview {
  week: string | null;
  stores: { name: string; products: number; updated: string }[];
  opportunities: ShelfGap[];
  risks: ShelfGap[];
  types: Record<ProductType, number>;
  skipped_dimensions: Record<ProductType, Dimension[]>;
  thresholds: { opportunity_share: number; risk_share: number; min_tagged: number };
}
