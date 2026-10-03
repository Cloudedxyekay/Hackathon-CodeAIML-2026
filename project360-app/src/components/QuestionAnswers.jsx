import { useEffect, useState } from "react";

export default function QuestionAnswers({ dashboard }) {
  const [answers, setAnswers] = useState(dashboard?.answers || []);

  useEffect(() => {
    fetch("/api/answers")
      .then((response) => response.json())
      .then(setAnswers);
  }, []);

  return (
    <section className="stack">
      {answers.map((item) => (
        <article key={item.id} className="panel qa">
          <div className="question-id">{item.id}</div>
          <div>
            <h3>{item.question}</h3>
            <p>{item.answer}</p>
            <p className="muted">Confidence: {item.confidence}</p>
            <div className="evidence-list compact">
              {(item.sources || []).map((source) => (
                <div key={`${item.id}-${source.file}`} className="source-line">
                  <strong>{source.file}</strong>
                  <span>{source.locator}</span>
                </div>
              ))}
            </div>
          </div>
        </article>
      ))}
    </section>
  );
}

