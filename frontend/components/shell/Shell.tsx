"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { Icon, type IconName } from "@/components/icons";
import { ago, stamp } from "@/lib/format";

const NAV: { href: string; label: string; icon: IconName }[] = [
  { href: "/", label: "Vue d'ensemble", icon: "overview" },
  { href: "/tendances", label: "Tendances", icon: "trends" },
  { href: "/demande", label: "Demande", icon: "demand" },
  { href: "/sources", label: "Sources", icon: "sources" },
];

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const root = document.documentElement;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const sync = () => setDark((root.dataset.theme ?? (mq.matches ? "dark" : "light")) === "dark");
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);
  function toggle() {
    const next = dark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("nn-theme", next); } catch {}
    setDark(!dark);
  }
  return (
    <button className="theme-toggle" type="button" aria-pressed={dark} onClick={toggle}>
      <Icon name="moon" />
      <span>Mode sombre</span>
      <span className="switch" aria-hidden="true"><span className="knob" /></span>
    </button>
  );
}

export function Shell({ lastUpdate, children }: { lastUpdate: string | null; children: ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  // Close the drawer after navigating (state adjusted during render, as React recommends).
  const [lastPath, setLastPath] = useState(pathname);
  if (pathname !== lastPath) {
    setLastPath(pathname);
    setOpen(false);
  }
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <header className="mobile-topbar">
        {/* eslint-disable-next-line @next/next/no-img-element -- small static brand asset */}
        <img src="/brand/noe-noah-logo-coral.png" alt="Noé & Noah" />
        <button className="icon-btn" type="button" aria-label={open ? "Fermer le menu" : "Ouvrir le menu"}
                aria-expanded={open} aria-controls="sidebar" onClick={() => setOpen(!open)}>
          <Icon name={open ? "close" : "menu"} />
        </button>
      </header>
      <div className={`sidebar-overlay${open ? " open" : ""}`} onClick={() => setOpen(false)} />

      <aside className={`sidebar${open ? " open" : ""}`} id="sidebar" aria-label="Navigation principale">
        <div className="sidebar-brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/brand/noe-noah-logo-coral.png" alt="Noé & Noah" width={120} height={63} />
        </div>
        <nav className="sidebar-nav">
          {NAV.map(item => (
            <Link key={item.href} className="nav-link" href={item.href}
                  aria-current={isActive(pathname, item.href) ? "page" : undefined}>
              <Icon name={item.icon} />
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div>
            {lastUpdate ? (
              <>
                <p className="updated">Mis à jour {ago(lastUpdate)}</p>
                <p className="updated-sub">{stamp(lastUpdate)}</p>
              </>
            ) : (
              <p className="updated">Aucune collecte terminée</p>
            )}
          </div>
          <ThemeToggle />
        </div>
      </aside>

      <main className="main">{children}</main>
    </>
  );
}
