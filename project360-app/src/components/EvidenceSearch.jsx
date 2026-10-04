import { useState } from "react";
import { Search } from "lucide-react";

export default function EvidenceSearch() {
  const [query, setQuery] = useState("INV-003");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  async function search(event) {
    event.preventDefault();
    if (loading || !query.trim()) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim(), limit: 12 })
      });
      if (!response.ok) throw new Error("La recherche est indisponible. Réessayez lorsque le serveur est accessible.");
      const data = await response.json();
      if (!Array.isArray(data.results)) throw new Error("Le serveur a renvoyé une réponse de recherche invalide.");
      setResults(data.results);
      setSearched(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="stack">
      <div className="panel">
        <label className="field-label" htmlFor="evidence-query">Evidence query</label>
        <form className="input-row" onSubmit={search}>
          <input id="evidence-query" value={query} onChange={(event) => setQuery(event.target.value)} />
          <button className="primary" type="submit" disabled={loading || !query.trim()}>
            <Search size={17} />
            {loading ? "Recherche…" : "Search"}
          </button>
        </form>
        {error && <p className="memory-error" role="alert">{error}</p>}
        {!error && searched && !results.length && <p role="status">Aucun document ne correspond à cette recherche.</p>}
      </div>
      <div className="evidence-list">
        {results.map((result) => (
          <article key={result.id} className="evidence-card">
            <strong>{result.title}</strong>
            <span>{result.path} | {result.locator} | score {result.score}</span>
            <p>{result.text}</p>
            <div className="tags">{result.tags?.map((tag) => <b key={tag}>{tag}</b>)}</div>
          </article>
        ))}
      </div>
    </section>
  );
}

