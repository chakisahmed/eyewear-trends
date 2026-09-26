"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

/** Underline tabs that write one URL parameter (each tab is a link, so it works without JS too). */
export function UrlTabs({ param, options, current, label, reset = [] }: {
  param: string;
  options: { value: string; label: string }[];
  current: string;
  label: string;
  /** Parameters to drop when switching tab (e.g. a page number). */
  reset?: string[];
}) {
  const pathname = usePathname();
  const params = useSearchParams();
  const href = (value: string) => {
    const next = new URLSearchParams(params.toString());
    next.set(param, value);
    reset.forEach(r => next.delete(r));
    return `${pathname}?${next}`;
  };
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {options.map(o => (
        <Link key={o.value} className="tab" role="tab" href={href(o.value)} aria-selected={o.value === current}
              scroll={false}>
          {o.label}
        </Link>
      ))}
    </div>
  );
}

/** A <select> bound to one URL parameter; the empty value removes the parameter. */
export function UrlSelect({ param, options, current, label, reset = [], className = "select", id, disabled }: {
  param: string;
  options: { value: string; label: string }[];
  current: string;
  label: string;
  reset?: string[];
  className?: string;
  /** With an id, a visible <label htmlFor> names the select instead of aria-label. */
  id?: string;
  disabled?: boolean;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  return (
    <select className={className} id={id} aria-label={id ? undefined : label} value={current} disabled={disabled} onChange={e => {
      const next = new URLSearchParams(params.toString());
      if (e.target.value) next.set(param, e.target.value); else next.delete(param);
      reset.forEach(r => next.delete(r));
      router.push(`${pathname}${next.size ? `?${next}` : ""}`, { scroll: false });
    }}>
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}
