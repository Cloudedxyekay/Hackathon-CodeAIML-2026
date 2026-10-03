import { useState } from "react";
import { FileText, Mail, Send, Table2 } from "lucide-react";

const sourceIcons = {
  email: Mail,
  spreadsheet: Table2,
  document: FileText,
  note: FileText,
  source: FileText
};

export default function AskAgent() {
  const [question, setQuestion] = useState("Quelle est la date de mise en production actuellement approuvee?");
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function ask() {
    if (!question.trim()) {
      setError("Enter a question for NOVA first.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      });

      if (!response.ok) {
        throw new Error("NOVA could not answer right now.");
      }

      setAnswer(await response.json());
    } catch (event) {
      setError(event.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="stack">
      <div className="panel">
        <p className="eyebrow">Ask NOVA Agent</p>
        <label className="field-label">Question</label>
        <div className="input-row">
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                ask();
              }
            }}
          />
          <button className="primary" onClick={ask} disabled={loading}>
            <Send size={17} />
            {loading ? "Searching" : "Ask NOVA"}
          </button>
        </div>
        {error && <p className="error-text">{error}</p>}
      </div>
      {answer && (
        <div className="panel">
          <div className="answer-header">
            <div>
              <p className="answer-text"><strong>Answer: </strong> {answer.answer}</p>
            </div>
            <div className="answer-badges">
              <span className="reasoning-mode">{answer.reasoning_mode ?? "local"}</span>
            </div>
          </div>

          <div className="references-block">
            <p className="section-label">References used</p>
            <ol className="reference-list">
              {(answer.references ?? []).map((reference) => {
                const Icon = sourceIcons[reference.type] ?? FileText;

                return (
                  <li key={reference.file}>
                    <Icon size={16} />
                    <div>
                      <strong>{reference.title}</strong>
                      <span>
                        {reference.type}
                        {reference.date ? ` | dated ${reference.date}` : ""}
                        {` | ${reference.file} | ${reference.locator}`}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>

          <p className="section-label">Exact excerpts</p>
          <div className="evidence-list">
            {(answer.excerpts ?? answer.evidence ?? []).map((item) => (
              <article key={`${item.file}-${item.locator}`} className="evidence-card">
                <strong>{item.file}</strong>
                <span>
                  {item.locator}
                  {item.date ? ` | dated ${item.date}` : ""}
                  {` | score ${item.score}`}
                </span>
                <blockquote>{item.excerpt}</blockquote>
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
