export default function Dashboard({ dashboard }) {
  const baseline = dashboard?.baseline ?? {};
  const actions = dashboard?.actions ?? [];
  const timeline = dashboard?.timeline ?? [];

  return (
    <section className="page-grid">
      <div className="panel wide">
        <p className="eyebrow">Baseline</p>
        <h2>{baseline.status || "Waiting for ingestion"}</h2>
        <p>{baseline.scope}</p>
      </div>
      <div className="metric">
        <span>As of</span>
        <strong>{baseline.as_of || "Unknown"}</strong>
      </div>
      <div className="metric">
        <span>Timeline Events</span>
        <strong>{timeline.length}</strong>
      </div>
      <div className="metric">
        <span>Open Actions</span>
        <strong>{actions.filter((item) => item.status !== "done").length}</strong>
      </div>
      <div className="panel">
        <h3>Go-live</h3>
        <p>{baseline.go_live}</p>
      </div>
      <div className="panel">
        <h3>Budget</h3>
        <p>{baseline.budget}</p>
      </div>
      <div className="panel wide">
        <h3>Known Risks</h3>
        <ul className="clean-list">
          {(baseline.risks || []).map((risk) => <li key={risk}>{risk}</li>)}
        </ul>
      </div>
    </section>
  );
}

