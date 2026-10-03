import { useEffect, useState } from "react";

export default function BonusComparison() {
  const [brief, setBrief] = useState(null);

  useEffect(() => {
    fetch("/api/brief")
      .then((response) => response.json())
      .then(setBrief);
  }, []);

  if (!brief) return <div className="panel">Generating brief...</div>;

  return (
    <section className="page-grid">
      <div className="panel wide">
        <p className="eyebrow">Bonus</p>
        <h2>{brief.title}</h2>
        <p>{brief.status}</p>
      </div>
      <div className="panel">
        <h3>Top Points</h3>
        <ul className="clean-list">
          {brief.top_points.map((point) => <li key={point}>{point}</li>)}
        </ul>
      </div>
      <div className="panel">
        <h3>Risks</h3>
        <ul className="clean-list">
          {brief.risks.map((risk) => <li key={risk}>{risk}</li>)}
        </ul>
      </div>
      <div className="metric">
        <span>Timeline Events</span>
        <strong>{brief.timeline_events}</strong>
      </div>
    </section>
  );
}
