import { useState } from "react";
import { RefreshCw } from "lucide-react";

export default function UpdateSimulator() {
  const [eventText, setEventText] = useState("");
  const [analysis, setAnalysis] = useState(null);

  async function analyze() {
    const response = await fetch("/api/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_text: eventText })
    });
    setAnalysis(await response.json());
  }

  return (
    <section className="stack">
      <div className="panel">
        <label className="field-label">New event</label>
        <textarea
          value={eventText}
          onChange={(event) => setEventText(event.target.value)}
          placeholder="Paste the new challenge information here..."
        />
        <button className="primary" onClick={analyze}>
          <RefreshCw size={17} />
          Compare to baseline
        </button>
      </div>
      {analysis && (
        <div className="panel">
          <p className="eyebrow">Impact analysis</p>
          <h2>{analysis.summary}</h2>
          <p>{analysis.warning}</p>
          <ul className="clean-list">
            {analysis.changed_items.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      )}
    </section>
  );
}

