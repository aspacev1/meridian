/** Honest placeholder for nav destinations whose backend doesn't exist
 * yet -- these need Phase 4+ work (AI chat, task persistence, historical
 * executive-view data, glossary/DQ detail) before they can show real data.
 * Intentionally not filled with the prototype's mock data.
 */
export function PlaceholderPage({ title, note }: { title: string; note: string }) {
  return (
    <div className="placeholder-page">
      <h2>{title}</h2>
      <p>{note}</p>
    </div>
  );
}
