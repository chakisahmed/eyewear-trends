/* Noé & Noah dashboard: shared shell behavior (theme, drawer, demo banner, export menu, refresh)
   and shared components (frame-shape glyphs via [data-glyph], sparklines via .spark[data-points]).
   Load at the end of <body>. Extracted from screen A. */
(function () {
  "use strict";

  /* Each shell part runs only if its markup is on the page, so pages without the app shell
     (e.g. the print report) can still use the shared glyphs and sparklines below. */
  function byId(id) { return document.getElementById(id); }

  /* ---------- Theme toggle ---------- */
  var root = document.documentElement;
  var mq = window.matchMedia("(prefers-color-scheme: dark)");
  var themeBtn = byId("themeToggle");
  if (themeBtn) {
    var effectiveTheme = function () { return root.dataset.theme || (mq.matches ? "dark" : "light"); };
    var syncToggle = function () { themeBtn.setAttribute("aria-pressed", String(effectiveTheme() === "dark")); };
    themeBtn.addEventListener("click", function () {
      root.dataset.theme = effectiveTheme() === "dark" ? "light" : "dark";
      syncToggle();
    });
    if (mq.addEventListener) mq.addEventListener("change", syncToggle);
    syncToggle();
  }

  /* ---------- Mobile drawer ---------- */
  var sidebar = byId("sidebar"), overlay = byId("sidebarOverlay"), burger = byId("menuBtn");
  if (sidebar && overlay && burger) {
    var closeDrawer = function () {
      sidebar.classList.remove("open");
      overlay.classList.remove("open");
      burger.setAttribute("aria-expanded", "false");
    };
    burger.addEventListener("click", function () {
      var open = sidebar.classList.toggle("open");
      overlay.classList.toggle("open", open);
      burger.setAttribute("aria-expanded", String(open));
    });
    overlay.addEventListener("click", closeDrawer);
    sidebar.querySelectorAll(".nav-link").forEach(function (a) {
      a.addEventListener("click", function () {
        if (window.innerWidth <= 768) closeDrawer();
      });
    });
  }

  /* ---------- Demo banner ---------- */
  var banner = byId("demoBanner"), removeDemo = byId("removeDemo");
  if (banner && removeDemo) {
    removeDemo.addEventListener("click", function (e) {
      e.preventDefault();
      banner.remove();
    });
  }

  /* ---------- Export menu ---------- */
  var exportBtn = byId("exportBtn"), exportMenu = byId("exportMenu");
  if (exportBtn && exportMenu) {
    exportBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = exportMenu.classList.toggle("open");
      exportBtn.setAttribute("aria-expanded", String(open));
    });
    document.addEventListener("click", function (e) {
      if (!exportMenu.contains(e.target)) {
        exportMenu.classList.remove("open");
        exportBtn.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ---------- Refresh (loading state) ---------- */
  var refreshBtn = byId("refreshBtn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", function () {
      if (refreshBtn.disabled) return;
      refreshBtn.disabled = true;
      refreshBtn.classList.add("is-loading");
      refreshBtn.querySelector(".btn-label").textContent = "Collecte en cours…";
      setTimeout(function () {
        refreshBtn.disabled = false;
        refreshBtn.classList.remove("is-loading");
        refreshBtn.querySelector(".btn-label").textContent = "Actualiser les données";
      }, 2200);
    });
  }

  /* ---------- Frame-shape glyphs ---------- */
  var GLYPHS = {
    "cat-eye":
      '<path d="M2 9Q5.5 5 10 6.5L14.5 8.5Q16 9.5 16 12Q16 14.5 14.5 15.5L10 17.5Q5.5 19 2 15Q4 12 2 9Z"/>' +
      '<path d="M34 9Q30.5 5 26 6.5L21.5 8.5Q20 9.5 20 12Q20 14.5 21.5 15.5L26 17.5Q30.5 19 34 15Q32 12 34 9Z"/>' +
      '<path d="M16 11Q18 10 20 11"/>',
    "oversize":
      '<rect x="1.5" y="4" width="14" height="16" rx="6"/>' +
      '<rect x="20.5" y="4" width="14" height="16" rx="6"/>' +
      '<path d="M15.5 10.5Q18 9 20.5 10.5"/>',
    "geometric":
      '<path d="M10 4L15.5 7V13L10 16L4.5 13V7Z"/>' +
      '<path d="M26 4L31.5 7V13L26 16L20.5 13V7Z"/>' +
      '<path d="M15.5 11Q18 10 20.5 11"/>',
    "aviator":
      '<path d="M15.5 8Q14 5.5 10 5.5Q3.5 5.5 3 11Q2.7 15 6 17.5Q10 20 13 17Q15.5 14.5 15.5 8Z"/>' +
      '<path d="M20.5 8Q22 5.5 26 5.5Q32.5 5.5 33 11Q33.3 15 30 17.5Q26 20 23 17Q20.5 14.5 20.5 8Z"/>' +
      '<path d="M15.5 9Q18 8 20.5 9"/>',
    "round":
      '<circle cx="10" cy="12" r="7"/>' +
      '<circle cx="26" cy="12" r="7"/>' +
      '<path d="M17 10.8Q18 9.8 19 10.8"/>',
    "rectangle":
      '<rect x="2" y="7" width="14" height="10" rx="2.5"/>' +
      '<rect x="20" y="7" width="14" height="10" rx="2.5"/>' +
      '<path d="M16 10.5H20"/>',
    "square":
      '<rect x="3.5" y="5" width="12.5" height="14" rx="3.5"/>' +
      '<rect x="20" y="5" width="12.5" height="14" rx="3.5"/>' +
      '<path d="M16 10.5Q18 9.5 20 10.5"/>',
    "rimless":
      '<ellipse cx="10" cy="12" rx="6.5" ry="5" stroke-width="1.2" stroke-dasharray="1.8 2.2"/>' +
      '<ellipse cx="26" cy="12" rx="6.5" ry="5" stroke-width="1.2" stroke-dasharray="1.8 2.2"/>' +
      '<path d="M16.5 10.5Q18 9.5 19.5 10.5"/>' +
      '<path d="M3.5 10.5H1.5M32.5 10.5H34.5"/>'
  };
  document.querySelectorAll("[data-glyph]").forEach(function (el) {
    el.innerHTML =
      '<svg viewBox="0 0 36 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      (GLYPHS[el.dataset.glyph] || "") +
      "</svg>";
  });

  /* ---------- Sparklines (hand-written SVG, generated) ---------- */
  document.querySelectorAll(".spark[data-points]").forEach(function (svg) {
    var pts = svg.dataset.points.split(",").map(Number);
    var w = 72, h = 24, p = 3, n = pts.length;
    var lo = Math.min.apply(null, pts);
    var hi = Math.max.apply(null, pts);
    // Stretching every series to full height makes 8,8,9,8 look as dramatic as 3→14.
    // Use a range of at least 60 % of the peak value, centered on the data, never below 0.
    var span = Math.max(hi - lo, 0.6 * hi, 1);
    var min = Math.max(0, (hi + lo) / 2 - span / 2);
    var step = (w - 2 * p) / (n - 1);
    var coords = pts.map(function (v, i) {
      return [
        +(p + i * step).toFixed(2),
        +(h - p - ((v - min) / span) * (h - 2 * p)).toFixed(2)
      ];
    });
    var line = coords.map(function (c) { return c.join(","); }).join(" ");
    var last = coords[n - 1];
    svg.innerHTML =
      '<polyline points="' + line + '" fill="none" stroke="var(--series-1)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' +
      '<circle cx="' + last[0] + '" cy="' + last[1] + '" r="2.5" fill="var(--series-1)"/>';
  });
})();
