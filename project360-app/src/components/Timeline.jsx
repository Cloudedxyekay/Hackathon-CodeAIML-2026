import { useEffect, useState } from "react";

export default function Timeline({ dashboard }) {
  const [events, setEvents] = useState(dashboard?.timeline || []);

  useEffect(() => {
    fetch("/api/timeline")
      .then((response) => response.json())
      .then(setEvents);
  }, []);

  return (
    <section className="timeline">
      {events.map((event) => (
        <article key={`${event.date}-${event.title}`} className="timeline-event">
          <time>{event.date}</time>
          <div>
            <span>{event.type}</span>
            <h3>{event.title}</h3>
            <p>{event.summary}</p>
            <p className="muted">{(event.sources || []).join(", ")}</p>
          </div>
        </article>
      ))}
    </section>
  );
}

