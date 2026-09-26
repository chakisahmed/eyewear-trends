import type { Metadata } from "next";
import { Inter, Montserrat } from "next/font/google";

import "./styles/shared.css";
import "./styles/screens.css";
import "./styles/report.css";
import "./styles/app.css";

// shared.css reads these through --font-body / --font-heading.
const inter = Inter({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--nf-inter", display: "swap" });
const montserrat = Montserrat({ subsets: ["latin"], weight: ["600", "700"], variable: "--nf-montserrat", display: "swap" });

export const metadata: Metadata = {
  title: { default: "Tendances lunettes · Noé & Noah", template: "%s · Noé & Noah" },
  description: "Veille IA des tendances lunettes (formes, couleurs, matières, styles) pour l'équipe achats Noé & Noah.",
};

// Apply the saved theme before first paint (no light flash for dark-mode users).
const THEME_SCRIPT = `try{var t=localStorage.getItem("nn-theme");if(t==="dark"||t==="light")document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="fr" className={`${inter.variable} ${montserrat.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
