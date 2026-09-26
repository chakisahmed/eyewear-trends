// Frame-shape glyphs: two lenses + bridge, drawn on a 36 × 24 box (from the mockups' shared glyph set).
// Keys are the backend taxonomy shape codes.

const G: Record<string, string> = {
  cat_eye:
    '<path d="M2 9Q5.5 5 10 6.5L14.5 8.5Q16 9.5 16 12Q16 14.5 14.5 15.5L10 17.5Q5.5 19 2 15Q4 12 2 9Z"/>' +
    '<path d="M34 9Q30.5 5 26 6.5L21.5 8.5Q20 9.5 20 12Q20 14.5 21.5 15.5L26 17.5Q30.5 19 34 15Q32 12 34 9Z"/><path d="M16 11Q18 10 20 11"/>',
  oversized:
    '<rect x="1.5" y="4" width="14" height="16" rx="6"/><rect x="20.5" y="4" width="14" height="16" rx="6"/><path d="M15.5 10.5Q18 9 20.5 10.5"/>',
  geometric:
    '<path d="M10 4L15.5 7V13L10 16L4.5 13V7Z"/><path d="M26 4L31.5 7V13L26 16L20.5 13V7Z"/><path d="M15.5 11Q18 10 20.5 11"/>',
  aviator:
    '<path d="M15.5 8Q14 5.5 10 5.5Q3.5 5.5 3 11Q2.7 15 6 17.5Q10 20 13 17Q15.5 14.5 15.5 8Z"/>' +
    '<path d="M20.5 8Q22 5.5 26 5.5Q32.5 5.5 33 11Q33.3 15 30 17.5Q26 20 23 17Q20.5 14.5 20.5 8Z"/><path d="M15.5 9Q18 8 20.5 9"/>',
  round: '<circle cx="10" cy="12" r="7"/><circle cx="26" cy="12" r="7"/><path d="M17 10.8Q18 9.8 19 10.8"/>',
  oval: '<ellipse cx="10" cy="12" rx="7.5" ry="5.5"/><ellipse cx="26" cy="12" rx="7.5" ry="5.5"/><path d="M17.5 11Q18 10.3 18.5 11"/>',
  rectangle: '<rect x="2" y="7" width="14" height="10" rx="2.5"/><rect x="20" y="7" width="14" height="10" rx="2.5"/><path d="M16 10.5H20"/>',
  square: '<rect x="3.5" y="5" width="12.5" height="14" rx="3.5"/><rect x="20" y="5" width="12.5" height="14" rx="3.5"/><path d="M16 10.5Q18 9.5 20 10.5"/>',
  browline:
    '<path d="M2 8.5h14" stroke-width="3"/><path d="M20 8.5h14" stroke-width="3"/><path d="M3 9Q3 17 9 17Q15 17 15 9"/><path d="M21 9Q21 17 27 17Q33 17 33 9"/><path d="M16 9h4"/>',
  wayfarer: '<path d="M2 7h14l-1.5 9.5Q14 18 12.5 18h-7Q4 18 3.5 16.5Z"/><path d="M20 7h14l-1.5 9.5Q32 18 30.5 18h-7Q22 18 21.5 16.5Z"/><path d="M16 9h4"/>',
  rimless:
    '<ellipse cx="10" cy="12" rx="6.5" ry="5" stroke-width="1.2" stroke-dasharray="1.8 2.2"/>' +
    '<ellipse cx="26" cy="12" rx="6.5" ry="5" stroke-width="1.2" stroke-dasharray="1.8 2.2"/><path d="M16.5 10.5Q18 9.5 19.5 10.5"/><path d="M3.5 10.5H1.5M32.5 10.5H34.5"/>',
  shield: '<path d="M2 8Q18 4 34 8Q34 15 27 17Q22 18 18 14Q14 18 9 17Q2 15 2 8Z"/>',
  butterfly: '<path d="M16 9Q10 4 2 7Q3 16 9 17Q15 17 16 11Z"/><path d="M20 9Q26 4 34 7Q33 16 27 17Q21 17 20 11Z"/><path d="M16 10h4"/>',
};

export function Glyph({ code, className = "trend-visual" }: { code: string; className?: string }) {
  return (
    <span className={className} aria-hidden="true">
      <svg viewBox="0 0 36 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round"
           strokeLinejoin="round" dangerouslySetInnerHTML={{ __html: G[code] ?? G.round }} />
    </span>
  );
}
