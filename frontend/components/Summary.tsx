import type { ReactNode } from "react";

// Renders the LLM weekly summary (French): "- " / "• " lines become bullets, other lines become the
// closing action box; **bold** is kept. Plain text only: no HTML from the model is ever injected.

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : part,
  );
}

export function SummaryBody({ text }: { text: string }) {
  const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
  const bullets = lines.filter(l => /^[-•*]\s+/.test(l)).map(l => l.replace(/^[-•*]\s+/, ""));
  const rest = lines.filter(l => !/^[-•*]\s+/.test(l));
  return (
    <>
      {bullets.length > 0 && (
        <ul className="summary-list">
          {bullets.map((b, i) => <li key={i}>{inline(b)}</li>)}
        </ul>
      )}
      {rest.map((p, i) => <div key={i} className="action-box">{inline(p)}</div>)}
    </>
  );
}
