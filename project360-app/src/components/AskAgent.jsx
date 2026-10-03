import { useState } from "react";
import { Send } from "lucide-react";

export default function AskAgent() {
  const [question, setQuestion] = useState("Quelle est la date de mise en production actuellement approuvee?");
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);

  async function ask() {
    setLoading(true);
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });
    setAnswer(await response.json());
    setLoading(false);
  }

  return (
    <section className="stack">
      <div className="panel">
        <label className="field-label">Question</label>
        <div className="input-row">
          <input value={question} onChange={(event) => setQuestion(event.target.value)} />
          <button className="primary" onClick={ask} disabled={loading}>
            <Send size={17} />
            {loading ? "Searching" : "Ask"}
          </button>
        </div>
      </div>
      {answer && (
        <div className="panel">
          <p className="eyebrow">Answer confidence: {answer.confidence}</p>
          <h2>{answer.answer}</h2>
          <p className="muted">{answer.uncertainty}</p>
          <div className="evidence-list">
            {answer.evidence.map((item) => (
              <article key={`${item.file}-${item.locator}`} className="evidence-card">
                <strong>{item.file}</strong>
                <span>{item.locator} | score {item.score}</span>
                <p>{item.excerpt}</p>
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

