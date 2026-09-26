export default function Loading() {
  return (
    <div aria-busy="true" aria-label="Chargement">
      <div className="skeleton skeleton-line" style={{ width: 280, height: 28 }} />
      <div className="skeleton skeleton-line" style={{ width: 360 }} />
      <div className="skeleton-grid">
        {Array.from({ length: 4 }, (_, i) => <div key={i} className="skeleton skeleton-block" />)}
      </div>
    </div>
  );
}
