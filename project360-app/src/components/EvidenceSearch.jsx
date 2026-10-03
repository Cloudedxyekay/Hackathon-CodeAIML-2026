import { useState } from "react";
import { Search } from "lucide-react";

export default function EvidenceSearch() {
  const [query, setQuery] = useState("INV-003");
  const [results, setResults] = useState([]);

  async function search() {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit: 12 })
    });
    const data = await response.json();
    setResults(data.results);
  }

  return (
    <section className="stack">
      <div className="panel">
        <label className="field-label">Evidence query</label>
        <div className="input-row">
          <input value={query} onChange={(event) => setQuery(event.target.value)} />
          <button className="primary" onClick={search}>
            <Search size={17} />
            Search
          </button>
        </div>
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

