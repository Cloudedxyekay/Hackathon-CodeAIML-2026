import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Download,
  FileText,
  Flag,
  GitBranch,
  Layers3,
  ListFilter,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  UserRound,
  X,
} from "lucide-react";

const TYPES = {
  decision: "Décision",
  milestone: "Jalon",
  validation: "Validation",
  risk: "Risque",
  delivery: "Livraison",
  proposal: "Proposition",
  update: "Suivi",
};
const STATES = {
  approved: "Approuvé",
  conditional: "Conditionnel",
  not_approved: "Non approuvé",
  completed: "Validé / fermé",
  delivered: "Livré",
  in_review: "En validation",
  open: "Ouvert",
  proposed: "Proposé",
  planned: "Planifié",
  in_progress: "En cours",
  reported: "Mentionné",
  superseded: "Date périmée",
};
const ICONS = {
  decision: GitBranch,
  milestone: Flag,
  validation: ShieldCheck,
  risk: TriangleAlert,
  delivery: Layers3,
  proposal: Clock3,
  update: FileText,
};
export const parseDate = (value) => new Date(`${value?.slice(0, 10)}T12:00:00`);
export const formatDate = (
  value,
  options = { day: "numeric", month: "short" },
) =>
  value && /^\d{4}-\d{2}-\d{2}/.test(value)
    ? parseDate(value).toLocaleDateString("fr-CA", options)
    : "Non précisée";
const iso = (value) =>
  `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
const today = () => iso(new Date());
const shortName = (path) => path.split("/").pop();
const initials = (name) =>
  name
    ? name
        .split(" ")
        .slice(0, 2)
        .map((part) => part[0])
        .join("")
    : "?";
const searchText = (text) =>
  text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

function download(name, body, type) {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function exportCalendar(events) {
  const escape = (text) =>
    String(text || "")
      .replace(/\\/g, "\\\\")
      .replace(/\r?\n/g, "\\n")
      .replace(/,/g, "\\,")
      .replace(/;/g, "\\;");
  const stamp = new Date()
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\.\d{3}/, "");
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//NOVA//Project Memory//FR",
    "CALSCALE:GREGORIAN",
  ];
  for (const item of events.filter((event) => event.date)) {
    const end = parseDate(item.end_date || item.date);
    end.setDate(end.getDate() + 1);
    lines.push(
      "BEGIN:VEVENT",
      `UID:${item.id}@nova.local`,
      `DTSTAMP:${stamp}`,
      `DTSTART;VALUE=DATE:${item.date.replaceAll("-", "")}`,
      `DTEND;VALUE=DATE:${iso(end).replaceAll("-", "")}`,
      `SUMMARY:${escape(item.title)}`,
      `DESCRIPTION:${escape(`${STATES[item.status]} · ${item.date_kind === "planned" ? "Date planifiée" : "Observation documentaire"}\n${item.summary}\n${item.evidence.map((source) => `${source.path} (${source.locator})`).join("\n")}`)}`,
      "TRANSP:TRANSPARENT",
      "END:VEVENT",
    );
  }
  lines.push("END:VCALENDAR");
  const folded = lines.map((line) => {
    let result = "",
      current = "",
      bytes = 0;
    for (const char of line) {
      const length = new TextEncoder().encode(char).length;
      if (bytes + length > 73) {
        result += current + "\r\n";
        current = " ";
        bytes = 1;
      }
      current += char;
      bytes += length;
    }
    return result + current;
  });
  download(
    "nova-calendrier.ics",
    folded.join("\r\n") + "\r\n",
    "text/calendar;charset=utf-8",
  );
}

async function loadProjectMemory(signal) {
  const direct = await fetch("/api/project-memory", { signal });
  if (direct.ok) return direct.json();
  const dashboard = await fetch("/api/dashboard", { signal });
  if (!dashboard.ok)
    throw new Error(
      "L'API est indisponible. Vérifiez que le serveur Python tourne sur le port 8000.",
    );
  const data = await dashboard.json();
  if (!data.memory)
    throw new Error("La mémoire du projet est absente de la réponse API.");
  return data.memory;
}

function SourceDrawer({ selection, close }) {
  const [sourceDocument, setSourceDocument] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const closeButton = useRef(null);
  const drawer = useRef(null);
  useEffect(() => {
    const previousFocus = document.activeElement;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButton.current?.focus();
    const keydown = (event) => {
      if (event.key === "Escape") close();
      if (event.key !== "Tab") return;
      const items = drawer.current?.querySelectorAll(
        "button:not(:disabled), a, input, [tabindex='0']",
      );
      if (!items?.length) return;
      const first = items[0],
        last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", keydown);
    return () => {
      window.removeEventListener("keydown", keydown);
      document.body.style.overflow = overflow;
      previousFocus?.focus();
    };
  }, [close]);
  useEffect(() => {
    setSourceDocument(null);
    setError("");
  }, [selection]);
  async function openDocument(source) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(
        `/api/documents/${encodeURIComponent(source.document_id)}`,
      );
      if (!response.ok) throw new Error("Impossible de charger ce document.");
      setSourceDocument(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }
  return (
    <div className="memory-overlay" onClick={close}>
      <aside
        ref={drawer}
        className="source-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="drawer-heading">
          <span className="memory-eyebrow">
            <FileText size={15} /> TRAÇABILITÉ
          </span>
          <button
            ref={closeButton}
            className="icon-button"
            onClick={close}
            aria-label="Fermer les sources"
          >
            <X size={20} />
          </button>
        </header>
        <h2 id="source-title">{selection.title}</h2>
        {selection.date && (
          <p className="muted">
            {formatDate(selection.date, {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
            {selection.end_date && selection.end_date !== selection.date
              ? ` au ${formatDate(selection.end_date, { day: "numeric", month: "long" })}`
              : ""}{" "}
            ·{" "}
            {selection.date_kind === "planned"
              ? "Date planifiée"
              : selection.date_kind === "received" ? "Date de réception — date source inconnue" : "Date de la source / du suivi"}
          </p>
        )}
        {selection.status && (
          <span className={`state-badge ${selection.status}`}>
            {STATES[selection.status]}
          </span>
        )}
        {selection.owner && (
          <p className="drawer-owner">
            <UserRound size={16} /> {selection.owner_role || "Référent cité"} :{" "}
            <strong>{selection.owner}</strong>
          </p>
        )}
        {selection.summary && (
          <p className="drawer-summary">{selection.summary}</p>
        )}
        {selection.ai_annotation && (
          <section className="ai-annotation">
            <span className="memory-eyebrow">
              <Sparkles size={15} /> EXTRACTION IA · À VÉRIFIER AVEC LES PREUVES
            </span>
            <h3>{selection.ai_annotation.title}</h3>
            <p>{selection.ai_annotation.summary}</p>
            {selection.ai_annotation.decision && (
              <p>
                <strong>Décision repérée :</strong>{" "}
                {selection.ai_annotation.decision}
              </p>
            )}
            <dl>
              <dt>Dates citées</dt>
              <dd>
                {selection.ai_annotation.dates
                  .map((value) =>
                    formatDate(value, {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    }),
                  )
                  .join(" · ") || "Aucune date explicite"}
              </dd>
              <dt>Acteurs cités</dt>
              <dd>
                {selection.ai_annotation.owners.join(" · ") || "Non précisés"}
              </dd>
            </dl>
            <blockquote>{selection.ai_annotation.excerpt}</blockquote>
          </section>
        )}
        <div className="source-intro">
          <ShieldCheck size={18} />
          <p>
            Chaque information est rattachée à un extrait. Les statuts décrivent
            ce que les documents attestent.
          </p>
        </div>
        {(selection.evidence || []).map((source, index) => (
          <section className="source-proof" key={`${source.path}-${index}`}>
            <div className="proof-heading">
              <span className="proof-number">{index + 1}</span>
              <div>
                <strong>{shortName(source.path)}</strong>
                <span>
                  {source.locator}
                  {source.published_on
                    ? ` · ${formatDate(source.published_on)}`
                    : " · publication non datée"}
                </span>
              </div>
            </div>
            <blockquote>{source.excerpt}</blockquote>
            <button
              className="text-button"
              disabled={loading}
              onClick={() => openDocument(source)}
            >
              Lire le document extrait <ArrowRight size={14} />
            </button>
          </section>
        ))}
        {error && (
          <p className="memory-error" role="alert">
            {error}
          </p>
        )}
        {sourceDocument && (
          <section className="full-document">
            <h3>{shortName(sourceDocument.path)}</h3>
            <pre>{sourceDocument.text}</pre>
          </section>
        )}
      </aside>
    </div>
  );
}

function EventCard({ event, topics, onSelect, compact = false }) {
  const Icon = ICONS[event.type] || FileText;
  return (
    <button
      className={`memory-event ${compact ? "compact-event" : ""}`}
      onClick={() => onSelect(event)}
    >
      <span className={`event-symbol ${event.type}`}>
        <Icon size={17} />
      </span>
      <div className="event-content">
        <div className="event-meta">
          <span className={`type-label ${event.type}`}>
            {TYPES[event.type]}
          </span>
          <span className="meta-dot">·</span>
          <span>{topics[event.topic]}</span>
          {event.date_kind === "planned" && (
            <span className="planned-label">Planifié</span>
          )}
          {event.date_kind === "received" && <span className="planned-label">Réception · date source inconnue</span>}
          {event.ai_annotation && (
            <span className="ai-label">
              <Sparkles size={10} /> Résumé IA
            </span>
          )}
        </div>
        <h3>{event.ai_annotation?.title || event.title}</h3>
        {!compact && (
          <p className="event-excerpt">
            {event.ai_annotation?.summary || event.summary}
          </p>
        )}
        <div className="event-footer">
          {event.owner ? (
            <span className="event-owner">
              <span className="avatar small">{initials(event.owner)}</span>
              {event.owner}
              <span className="owner-role">{event.owner_role}</span>
            </span>
          ) : (
            <span className="muted">Responsable non précisé</span>
          )}
          <span className="source-count">
            <FileText size={13} />
            {event.evidence.length} source{event.evidence.length > 1 ? "s" : ""}
          </span>
        </div>
      </div>
      <span className={`state-badge ${event.status}`}>
        {STATES[event.status]}
      </span>
      <ChevronRight className="event-chevron" size={16} />
    </button>
  );
}

function ActivityStrip({ events, month, setMonth }) {
  const months = useMemo(() => {
    const counts = {};
    for (const event of events)
      if (event.date)
        counts[event.date.slice(0, 7)] =
          (counts[event.date.slice(0, 7)] || 0) + 1;
    return Object.entries(counts).sort(([a], [b]) => a.localeCompare(b));
  }, [events]);
  const maximum = Math.max(1, ...months.map(([, count]) => count));
  return (
    <div className="activity-strip">
      <div>
        <span className="memory-eyebrow">LE FIL DU PROJET</span>
        <p>Sélectionnez une période</p>
      </div>
      <div className="activity-months">
        {months.map(([key, count]) => (
          <button
            key={key}
            className={month === key ? "selected" : ""}
            onClick={() => setMonth(month === key ? "" : key)}
            aria-pressed={month === key}
            title={`${count} événements`}
          >
            <span className="activity-bar">
              <i
                style={{ height: `${Math.max(15, (count / maximum) * 100)}%` }}
              />
            </span>
            <span>{formatDate(`${key}-01`, { month: "short" })}</span>
            <b>{count}</b>
          </button>
        ))}
      </div>
      <span className="activity-caption">
        <i /> Événements documentés
      </span>
    </div>
  );
}

function Calendar({ events, allEvents, memory, onSelect }) {
  const referenceDay = allEvents.filter(event => event.date && event.date_kind !== "planned").map(event => event.date).sort().at(-1) || memory.as_of || today();
  const [month, setMonth] = useState(() =>
    referenceDay.slice(0, 7),
  );
  const [selected, setSelected] = useState(referenceDay);
  const first = parseDate(`${month}-01`),
    start = new Date(first);
  start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
  const days = Array.from({ length: 42 }, (_, index) => {
    const day = new Date(start);
    day.setDate(start.getDate() + index);
    return iso(day);
  });
  const byDate = useMemo(() => {
    const groups = {};
    for (const day of days)
      groups[day] = events.filter(
        (event) =>
          event.date &&
          event.date <= day &&
          (event.end_date || event.date) >= day,
      );
    return groups;
  }, [events, month]);
  function navigate(offset) {
    const next = parseDate(`${month}-01`);
    next.setMonth(next.getMonth() + offset);
    setMonth(iso(next).slice(0, 7));
    setSelected(iso(next));
  }
  const selectedEvents = byDate[selected] || [];
  const monthEnd = iso(new Date(first.getFullYear(), first.getMonth() + 1, 0));
  const monthCount = events.filter(
    (event) =>
      event.date &&
      event.date <= monthEnd &&
      (event.end_date || event.date) >= `${month}-01`,
  ).length;
  const hiddenCount =
    allEvents.filter(
      (event) =>
        event.date &&
        event.date <= selected &&
        (event.end_date || event.date) >= selected,
    ).length - selectedEvents.length;
  return (
    <div className="calendar-layout">
      <section className="calendar-panel">
        <header className="calendar-header">
          <div>
            <h2>
              {formatDate(`${month}-01`, { month: "long", year: "numeric" })}
            </h2>
            <span>{monthCount} événements ce mois-ci</span>
          </div>
          <div className="calendar-navigation">
            <button
              className="quiet-button"
              onClick={() => {
                setMonth(today().slice(0, 7));
                setSelected(today());
              }}
            >
              Aujourd’hui
            </button>
            <button
              className="icon-button"
              onClick={() => navigate(-1)}
              aria-label="Mois précédent"
            >
              <ChevronLeft size={18} />
            </button>
            <button
              className="icon-button"
              onClick={() => navigate(1)}
              aria-label="Mois suivant"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </header>
        <div className="calendar-weekdays">
          {["LUN", "MAR", "MER", "JEU", "VEN", "SAM", "DIM"].map((day) => (
            <span key={day}>{day}</span>
          ))}
        </div>
        <div className="calendar-grid">
          {days.map((day) => (
            <button
              key={day}
              className={`calendar-day ${day.startsWith(month) ? "" : "other-month"} ${day === selected ? "selected" : ""} ${day === today() ? "is-today" : ""}`}
              onClick={() => setSelected(day)}
              aria-pressed={day === selected}
              aria-label={`${formatDate(day, { day: "numeric", month: "long" })}, ${(byDate[day] || []).length} événements`}
            >
              <span className="day-number">{parseDate(day).getDate()}</span>
              <span className="day-events">
                {(byDate[day] || []).slice(0, 2).map((event) => (
                  <span
                    key={event.id}
                    className={`calendar-event ${event.type}`}
                  >
                    <i />
                    {event.title}
                  </span>
                ))}
                {(byDate[day] || []).length > 2 && (
                  <span className="more-events">
                    +{byDate[day].length - 2} autres
                  </span>
                )}
              </span>
            </button>
          ))}
        </div>
        <footer className="calendar-legend">
          <span>
            <i className="decision" /> Décisions
          </span>
          <span>
            <i className="milestone" /> Jalons
          </span>
          <span>
            <i className="risk" /> Risques
          </span>
          <span>
            <i className="validation" /> Validations
          </span>
        </footer>
      </section>
      <aside className="day-agenda">
        <span className="memory-eyebrow">AGENDA DU JOUR</span>
        <h2>{formatDate(selected, { day: "numeric", month: "long" })}</h2>
        <p className="muted">
          {selectedEvents.length} événement
          {selectedEvents.length > 1 ? "s" : ""}
          {hiddenCount > 0 ? ` · ${hiddenCount} masqué(s) par les filtres` : ""}
        </p>
        <div className="agenda-events">
          {selectedEvents.length ? (
            selectedEvents.map((event) => (
              <EventCard
                key={event.id}
                event={event}
                topics={memory.topics}
                onSelect={onSelect}
                compact
              />
            ))
          ) : (
            <div className="memory-empty">
              <CalendarDays size={28} />
              <h3>Aucun événement</h3>
              <p>Sélectionnez une autre journée ou ajustez les filtres.</p>
            </div>
          )}
        </div>
        <div className="agenda-note">
          <Clock3 size={16} />
          <span>
            Les dates planifiées sont des cibles, pas des réalisations
            attestées.
          </span>
        </div>
      </aside>
    </div>
  );
}

function Progress({ memory, onSelect }) {
  const { tickets, phases, progress } = memory;
  const min = phases.length
    ? Math.min(...phases.map((phase) => parseDate(phase.start).getTime()))
    : 0;
  const max = phases.length
    ? Math.max(
        ...phases.map((phase) => parseDate(phase.end).getTime()),
        memory.schedule.current_target
          ? parseDate(memory.schedule.current_target).getTime()
          : 0,
      )
    : 1;
  const span = Math.max(86400000, max - min),
    datePosition = (value) => ((parseDate(value).getTime() - min) / span) * 100;
  const plot = useMemo(() => {
    if (!progress.length) return null;
    const first = parseDate(progress[0].date).getTime(),
      last = parseDate(progress.at(-1).date).getTime();
    const position = (point, key) => [
      36 +
        ((parseDate(point.date).getTime() - first) /
          Math.max(1, last - first)) *
          660,
      172 - (point[key] / Math.max(1, tickets.length)) * 138,
    ];
    const step = (key) =>
      progress
        .map((point, index) => {
          const [x, y] = position(point, key);
          return index ? `H${x} V${y}` : `M${x},${y}`;
        })
        .join(" ");
    return {
      created: step("created"),
      closed: step("closed"),
      first: progress[0].date,
      last: progress.at(-1).date,
    };
  }, [progress, tickets.length]);
  return (
    <div className="progress-workspace">
      <section className="memory-panel">
        <div className="section-heading">
          <div>
            <span className="memory-eyebrow">TRAJECTOIRE DE RÉSOLUTION</span>
            <h2>Des signalements aux validations</h2>
          </div>
          <span className="chart-legend">
            <i className="created-line" /> Signalés{" "}
            <i className="closed-line" /> Fermés
          </span>
        </div>
        {plot ? (
          <svg
            className="progress-chart"
            viewBox="0 0 730 210"
            role="img"
            aria-label={`Évolution des tickets : ${tickets.length} signalés et ${memory.stats.completed_tickets} fermés au ${memory.as_of}`}
          >
            {[0, 2, 4, 6, 8]
              .filter((n) => n <= tickets.length)
              .map((n) => (
                <g key={n}>
                  <line
                    x1="36"
                    x2="696"
                    y1={172 - (n / Math.max(1, tickets.length)) * 138}
                    y2={172 - (n / Math.max(1, tickets.length)) * 138}
                    stroke="#e8ecf3"
                    strokeDasharray="4 5"
                  />
                  <text
                    x="14"
                    y={176 - (n / Math.max(1, tickets.length)) * 138}
                  >
                    {n}
                  </text>
                </g>
              ))}
            <path
              d={plot.created}
              fill="none"
              stroke="#a5b4fc"
              strokeWidth="3"
            />
            <path
              d={plot.closed}
              fill="none"
              stroke="#14a58b"
              strokeWidth="3"
            />
            <text x="36" y="202">
              {formatDate(plot.first)}
            </text>
            <text x="696" y="202" textAnchor="end">
              {formatDate(plot.last)}
            </text>
          </svg>
        ) : (
          <p className="muted">Aucun historique de tickets daté.</p>
        )}
        <p className="chart-footnote">
          Fermetures datées à partir des validations explicites. Aucun
          avancement global estimé.
        </p>
      </section>
      <section className="memory-panel">
        <div className="section-heading">
          <div>
            <span className="memory-eyebrow">PLAN DOCUMENTÉ</span>
            <h2>Les étapes de la livraison</h2>
          </div>
          <span className="subtle-pill">Statuts déclarés dans le plan</span>
        </div>
        {phases.length ? (
          <div className="gantt-scroll">
            <div className="gantt">
              <div className="gantt-header">
                <span>Étape / responsable</span>
                <div>
                  {[0, 25, 50, 75, 100].map((percent) => (
                    <span key={percent} style={{ left: `${percent}%` }}>
                      {formatDate(iso(new Date(min + (span * percent) / 100)))}
                    </span>
                  ))}
                </div>
              </div>
              {phases.map((phase) => (
                <button
                  key={phase.id}
                  className="gantt-row"
                  onClick={() =>
                    onSelect({
                      ...phase,
                      date: phase.start,
                      date_kind: "planned",
                      summary:
                        phase.warning ||
                        `Du ${phase.start} au ${phase.end}. Statut déclaré dans le plan : ${STATES[phase.status]}.`,
                      owner_role: "Responsable du plan",
                    })
                  }
                >
                  <div className="gantt-label">
                    <strong>
                      {phase.title}
                      {phase.warning && <TriangleAlert size={14} />}
                    </strong>
                    <span>{phase.owner}</span>
                  </div>
                  <div className="gantt-track">
                    <span
                      className={`gantt-bar ${phase.status} ${phase.warning ? "stale" : ""}`}
                      style={{
                        left: `${datePosition(phase.start)}%`,
                        width: `${Math.max(1.2, datePosition(phase.end) - datePosition(phase.start))}%`,
                      }}
                    >
                      <span>{STATES[phase.status]}</span>
                    </span>
                  </div>
                </button>
              ))}
              {memory.schedule.current_target && (
                <div className="gantt-row target-row">
                  <div className="gantt-label">
                    <strong>Cible approuvée</strong>
                    <span>
                      {formatDate(memory.schedule.current_target)}
                      {memory.schedule.conditional ? " · conditionnelle" : ""}
                    </span>
                  </div>
                  <div className="gantt-track">
                    <span
                      className="gantt-target"
                      style={{
                        left: `${datePosition(memory.schedule.current_target)}%`,
                      }}
                    >
                      <Flag size={15} />
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <p className="muted">Aucun plan daté disponible.</p>
        )}
      </section>
      <section className="memory-panel">
        <div className="section-heading">
          <div>
            <span className="memory-eyebrow">REGISTRE DE SUIVI</span>
            <h2>Chaque ticket, son état, sa preuve</h2>
          </div>
          <span className="subtle-pill">{tickets.length} tickets</span>
        </div>
        <div className="ticket-table-wrap">
          <table className="ticket-table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Référent / demandeur</th>
                <th>Création</th>
                <th>Dernier suivi</th>
                <th>État documenté</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((ticket) => (
                <tr key={ticket.id}>
                  <td>
                    <button
                      className="ticket-link"
                      onClick={() =>
                        onSelect({
                          ...ticket,
                          date: ticket.last_update,
                          title: `${ticket.id} · ${ticket.title}`,
                        })
                      }
                    >
                      <strong>{ticket.id}</strong>
                      <span>{ticket.title}</span>
                    </button>
                  </td>
                  <td>{ticket.owner || "Non précisé"}</td>
                  <td>{formatDate(ticket.created_on)}</td>
                  <td>{formatDate(ticket.last_update)}</td>
                  <td>
                    <span className={`state-badge ${ticket.status}`}>
                      {STATES[ticket.status]}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function OwnerHistory({ memory, onSelect }) {
  if (!memory.assignments?.length) return null;
  return (
    <section className="insight-card">
      <span className="memory-eyebrow">
        <UserRound size={15} /> CHARGE DE PROJET
      </span>
      <div className="owner-history">
        {[...memory.assignments].reverse().map((assignment) => (
          <button
            key={`${assignment.effective_on}-${assignment.owner}`}
            onClick={() =>
              onSelect({
                ...assignment,
                title: `${assignment.owner} · charge de projet`,
                date: assignment.effective_on,
                summary: assignment.until
                  ? `Charge de projet du ${assignment.effective_on} jusqu’au transfert du ${assignment.until}.`
                  : `Attribution effective le ${assignment.effective_on}, selon les sources disponibles.`,
                owner_role: "Rôle explicitement attribué",
              })
            }
          >
            <span className="avatar">{initials(assignment.owner)}</span>
            <span>
              <strong>{assignment.owner}</strong>
              <small>
                {assignment.until
                  ? `${formatDate(assignment.effective_on)} → ${formatDate(assignment.until)}`
                  : `Depuis le ${formatDate(assignment.effective_on)}`}
              </small>
            </span>
            {!assignment.until && <span className="subtle-pill">Actuel</span>}
          </button>
        ))}
      </div>
      <p className="insight-footnote">
        Le rôle est attribué par une source explicite, pas par la liste des
        destinataires.
      </p>
    </section>
  );
}

export default function Timeline({
  dashboard,
  initialView = "timeline",
  onRefresh,
}) {
  const [memory, setMemory] = useState(dashboard?.memory || null),
    [view, setView] = useState(initialView);
  const [loading, setLoading] = useState(!dashboard?.memory),
    [rebuilding, setRebuilding] = useState(false),
    [enriching, setEnriching] = useState(false),
    [error, setError] = useState("");
  const [aiNotice, setAiNotice] = useState("");
  const [query, setQuery] = useState(""),
    [owner, setOwner] = useState(""),
    [type, setType] = useState(""),
    [topic, setTopic] = useState(""),
    [month, setMonth] = useState(""),
    [dateKind, setDateKind] = useState("");
  const [selection, setSelection] = useState(null);
  const closeDrawer = useMemo(() => () => setSelection(null), []);
  const [timelineOffset, setTimelineOffset] = useState(0);
  const timelineHeading = useRef(null);
  useEffect(() => {
    setView(initialView);
  }, [initialView]);
  useEffect(() => {
    const controller = new AbortController();
    loadProjectMemory(controller.signal)
      .then(setMemory)
      .catch((err) => {
        if (err.name !== "AbortError") setError(err.message);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);
  async function rebuild() {
    setRebuilding(true);
    setError("");
    try {
      const response = await fetch("/api/ingest", { method: "POST" });
      if (!response.ok)
        throw new Error(
          "L’analyse n’a pas pu terminer. Réessayez lorsque l’API est disponible.",
        );
      const result = await response.json();
      if (!result.ok) throw new Error(result.message || "Corpus introuvable.");
      setMemory(await loadProjectMemory());
      onRefresh?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setRebuilding(false);
    }
  }
  async function enrichWithAI() {
    setEnriching(true);
    setError("");
    setAiNotice("");
    try {
      const response = await fetch("/api/project-memory/enrich", {
        method: "POST",
      });
      const result = await response.json();
      if (!response.ok)
        throw new Error(
          result.detail || "L’enrichissement IA est indisponible.",
        );
      setMemory(result.memory);
      setAiNotice(
        `${result.accepted} événements enrichis par l’IA, avec citations vérifiées.${result.rejected ? ` ${result.rejected} annotations non sourcées écartées.` : ""}`,
      );
      onRefresh?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setEnriching(false);
    }
  }
  const events = useMemo(
    () =>
      (memory?.events || []).filter(
        (event) =>
          (!query ||
            searchText(
              `${event.title} ${event.summary} ${event.owner || ""} ${event.sources.join(" ")} ${event.ai_annotation?.title || ""} ${event.ai_annotation?.summary || ""}`,
            ).includes(searchText(query))) &&
          (!owner || event.owner === owner) &&
          (!type || event.type === type) &&
          (!topic || event.topic === topic) &&
          (!month || event.date?.startsWith(month)) &&
          (!dateKind || event.date_kind === dateKind),
      ),
    [memory, query, owner, type, topic, month, dateKind],
  );
  const pageSize = 10;
  const timelineToday = today();
  const sortedEvents = useMemo(
    () =>
      [...events].sort((a, b) =>
        (a.date || "9999-12-31").localeCompare(b.date || "9999-12-31"),
      ),
    [events],
  );
  const anchorIndex = useMemo(() => {
    if (!sortedEvents.length) return 0;
    const index = sortedEvents.findIndex(
      (event) => event.date && event.date >= timelineToday,
    );
    return index === -1
      ? Math.max(0, sortedEvents.length - pageSize)
      : index;
  }, [sortedEvents, timelineToday]);
  const hasTodayOrFuture = sortedEvents.some(
    (event) => event.date && event.date >= timelineToday,
  );
  const timelineStart =
    timelineOffset < 0
      ? Math.max(0, anchorIndex + timelineOffset * pageSize)
      : Math.min(anchorIndex + timelineOffset * pageSize, sortedEvents.length);
  const timelineEnd =
    timelineOffset < 0
      ? Math.max(
          timelineStart,
          Math.min(anchorIndex + (timelineOffset + 1) * pageSize, anchorIndex),
        )
      : Math.min(timelineStart + pageSize, sortedEvents.length);
  useEffect(() => {
    setTimelineOffset(0);
  }, [events]);
  const changeTimelineOffset = (offset) => {
    setTimelineOffset(offset);
    timelineHeading.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  const grouped = useMemo(() => {
    const groups = {};
    for (const event of sortedEvents.slice(timelineStart, timelineEnd))
      (groups[event.date || "undated"] ||= []).push(event);
    return Object.entries(groups);
  }, [sortedEvents, timelineStart, timelineEnd]);
  const filtered = Boolean(
    query || owner || type || topic || month || dateKind,
  );
  const resetFilters = () => {
    setQuery("");
    setOwner("");
    setType("");
    setTopic("");
    setMonth("");
    setDateKind("");
  };
  if (loading)
    return (
      <div className="memory-loading" role="status">
        <RefreshCw className="spinning" size={26} />
        <h2>Lecture de la mémoire du projet…</h2>
        <p>Dates, décisions et preuves documentaires.</p>
      </div>
    );
  if (!memory)
    return (
      <div className="memory-error" role="alert">
        <TriangleAlert size={22} />
        <h2>La mémoire du projet est indisponible</h2>
        <p>{error || "Démarrez le serveur Python pour charger le corpus."}</p>
        <button className="primary" onClick={() => window.location.reload()}>
          Réessayer
        </button>
      </div>
    );
  const percent = memory.stats.tickets
    ? Math.round((memory.stats.completed_tickets / memory.stats.tickets) * 100)
    : 0;
  return (
    <div className="memory-workspace">
      <section className="memory-hero">
        <div className="hero-copy">
          <span className="hero-kicker">
            <span /> MÉMOIRE VIVANTE DU PROJET
          </span>
          <h2>
            Chaque décision a une histoire.
            <br />
            <em>Retrouvez le fil.</em>
          </h2>
          <p>
            Des documents dispersés à une vision claire : ce qui a changé, qui
            intervient et ce qu’il reste à valider.
          </p>
          <div className="hero-baseline">
            <Clock3 size={14} /> Dernier fait documenté :{" "}
            {formatDate(memory.as_of, {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </div>
        </div>
        <div className="hero-target">
          <span className="target-icon">
            <Flag size={22} />
          </span>
          <span className="target-label">MISE EN PRODUCTION</span>
          <strong>
            {formatDate(memory.schedule.current_target, {
              day: "numeric",
              month: "long",
            })}
          </strong>
          <span className="target-year">
            {memory.schedule.current_target?.slice(0, 4) || "À confirmer"}
          </span>
          <span className="target-condition">
            <i />{" "}
            {memory.schedule.conditional
              ? "Cible conditionnelle"
              : "Cible documentée"}
          </span>
          {memory.schedule.delay_days > 0 && (
            <small>
              +{memory.schedule.delay_days} jours depuis la cible initiale
            </small>
          )}
        </div>
      </section>
      {aiNotice && (
        <div className="ai-notice" role="status">
          <Sparkles size={16} />
          <span>{aiNotice}</span>
          <button
            className="icon-button"
            onClick={() => setAiNotice("")}
            aria-label="Masquer le message"
          >
            <X size={14} />
          </button>
        </div>
      )}
      <section className="memory-metrics" aria-label="Indicateurs du corpus">
        <div>
          <span>
            <CalendarDays size={16} /> Événements extraits
          </span>
          <strong>
            {memory.stats.events}
            <small>{memory.stats.documents} documents analysés</small>
          </strong>
        </div>
        <div>
          <span>
            <GitBranch size={16} /> Décisions repérées
          </span>
          <strong>
            {memory.stats.decisions}
            <small>dont refus et conditions</small>
          </strong>
        </div>
        <div>
          <span>
            <UserRound size={16} /> Acteurs cités
          </span>
          <strong>
            {memory.stats.owners}
            <small>personnes et équipes</small>
          </strong>
        </div>
        <div>
          <span>
            <CheckCircle2 size={16} /> Tickets fermés
          </span>
          <strong>
            {memory.stats.completed_tickets}
            <b>/{memory.stats.tickets}</b>
            <small>validations documentées</small>
          </strong>
          <div className="metric-progress">
            <i style={{ width: `${percent}%` }} />
          </div>
        </div>
      </section>
      <div
        className={`memory-main-layout ${view === "calendar" ? "calendar-view" : ""}`}
      >
        <div className="memory-main-column">
          <div className="workspace-toolbar">
            <div
              className="view-switch"
              role="group"
              aria-label="Vue du projet"
            >
              {[
                { id: "timeline", label: "Chronologie", icon: GitBranch },
                { id: "calendar", label: "Calendrier", icon: CalendarDays },
                { id: "progress", label: "Avancement", icon: Layers3 },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  className={view === id ? "active" : ""}
                  onClick={() => {
                    if (id === "progress") resetFilters();
                    setView(id);
                  }}
                  aria-pressed={view === id}
                >
                  <Icon size={16} />
                  {label}
                </button>
              ))}
            </div>
            <div className="toolbar-actions">
              <button
                className="quiet-button"
                onClick={() => exportCalendar(events)}
                title="Exporter les événements filtrés vers un calendrier"
              >
                <Download size={15} /> .ics
              </button>
              <button
                className="quiet-button"
                onClick={rebuild}
                disabled={rebuilding || enriching}
              >
                <RefreshCw size={15} className={rebuilding ? "spinning" : ""} />
                {rebuilding ? "Analyse…" : "Ré-analyser"}
              </button>
              <button
                className="quiet-button ai-button"
                onClick={enrichWithAI}
                disabled={enriching || rebuilding}
              >
                <Sparkles size={15} className={enriching ? "spinning" : ""} />
                {enriching ? "Extraction IA…" : "Enrichir IA"}
              </button>
            </div>
          </div>
          {error && (
            <p className="memory-error" role="alert">
              {error}
            </p>
          )}
          {view !== "progress" && (
            <>
              <div className="memory-filters">
                <label className="memory-search">
                  <Search size={17} />
                  <input
                    aria-label="Rechercher dans les événements"
                    placeholder="Une décision, un ticket, un responsable…"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                </label>
                <div className="filter-selects">
                  <select
                    aria-label="Type d’événement"
                    value={type}
                    onChange={(event) => setType(event.target.value)}
                  >
                    <option value="">Tous les types</option>
                    {Object.entries(TYPES).map(([id, label]) => (
                      <option key={id} value={id}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label="Acteur cité"
                    value={owner}
                    onChange={(event) => setOwner(event.target.value)}
                  >
                    <option value="">Tous les acteurs</option>
                    {memory.owners.map((item) => (
                      <option key={item.name}>{item.name}</option>
                    ))}
                  </select>
                  <select
                    aria-label="Sujet"
                    value={topic}
                    onChange={(event) => setTopic(event.target.value)}
                  >
                    <option value="">Tous les sujets</option>
                    {Object.entries(memory.topics).map(([id, label]) => (
                      <option key={id} value={id}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label="Nature de la date"
                    value={dateKind}
                    onChange={(event) => setDateKind(event.target.value)}
                  >
                    <option value="">Faits et planification</option>
                    <option value="observed">Faits documentés</option>
                    <option value="planned">Dates planifiées</option>
                    <option value="received">Réceptions sans date source</option>
                  </select>
                </div>
              </div>
              {filtered && (
                <div className="filter-summary">
                  <ListFilter size={14} />
                  <span>
                    {events.length} événements correspondent
                    {month
                      ? ` · ${formatDate(`${month}-01`, { month: "long", year: "numeric" })}`
                      : ""}
                  </span>
                  <button onClick={resetFilters}>
                    Effacer les filtres <X size={13} />
                  </button>
                </div>
              )}
            </>
          )}
          {view === "timeline" && (
            <>
              <ActivityStrip
                events={memory.events}
                month={month}
                setMonth={setMonth}
              />
              <div className="timeline-list-heading" ref={timelineHeading}>
                <span>
                  {events.length} événements · départ aujourd'hui, preuves au clic
                </span>
                <button
                  className="text-button"
                  onClick={() => changeTimelineOffset(0)}
                  disabled={timelineOffset === 0}
                >
                  <Clock3 size={14} />
                  Revenir à aujourd'hui
                </button>
              </div>
              <div className="chronology">
                {grouped.length ? (
                  grouped.map(([day, items]) => (
                    <section key={day} className="chronology-day">
                      <div className="chronology-date">
                        <span className="timeline-node" />
                        <time dateTime={day === "undated" ? undefined : day}>
                          <strong>
                            {formatDate(day, {
                              day: "numeric",
                              month: "short",
                            })}
                          </strong>
                          <span>
                            {day === "undated"
                              ? "Date inconnue"
                              : day.slice(0, 4)}
                          </span>
                        </time>
                        <span className="date-event-count">{items.length}</span>
                      </div>
                      <div className="chronology-events">
                        {items.map((item) => (
                          <EventCard
                            key={item.id}
                            event={item}
                            topics={memory.topics}
                            onSelect={setSelection}
                          />
                        ))}
                      </div>
                    </section>
                  ))
                ) : (
                  <div className="memory-empty">
                    <Search size={30} />
                    <h3>Aucun événement ne correspond</h3>
                    <p>Essayez un autre mot-clé ou effacez les filtres.</p>
                    <button className="quiet-button" onClick={resetFilters}>
                      Effacer les filtres
                    </button>
                  </div>
                )}
              </div>
              {events.length > 0 && (
                <nav className="timeline-pagination" aria-label="Pages de la chronologie">
                  <span aria-live="polite">
                    Événements {timelineStart + 1}–{timelineEnd} sur {events.length}
                  </span>
                  <div>
                    <button className="quiet-button" disabled={timelineStart === 0}
                      onClick={() => changeTimelineOffset(timelineOffset - 1)} aria-label="Voir les événements passés">
                      <ChevronLeft size={16} /> Passé
                    </button>
                    <span>
                      {timelineOffset < 0
                        ? "Historique"
                        : timelineOffset > 0
                          ? "Suite"
                          : hasTodayOrFuture
                            ? "Aujourd'hui et suite"
                            : "Derniers événements"}
                    </span>
                    <button className="quiet-button" disabled={timelineEnd >= events.length}
                      onClick={() => changeTimelineOffset(timelineOffset + 1)} aria-label="Voir les événements suivants">
                      Plus tard <ChevronRight size={16} />
                    </button>
                  </div>
                </nav>
              )}
            </>
          )}
          {view === "calendar" && (
            <Calendar
              events={events}
              allEvents={memory.events}
              memory={memory}
              onSelect={setSelection}
            />
          )}
          {view === "progress" && (
            <Progress memory={memory} onSelect={setSelection} />
          )}
        </div>
        {view !== "calendar" && (
          <aside className="memory-insights">
            <section className="insight-card gate-card">
              <span className="memory-eyebrow">
                <ShieldCheck size={15} /> AVANT LA PRODUCTION
              </span>
              <h3>{memory.gates.length} conditions à fermer</h3>
              <p>
                La cible est approuvée.
                <br />
                Le passage en production reste à valider.
              </p>
              <div className="gate-list">
                {memory.gates.map((gate) => (
                  <button
                    key={gate.id}
                    onClick={() =>
                      setSelection({
                        ...gate,
                        title: `${gate.id} · ${gate.title}`,
                        date: gate.last_update,
                      })
                    }
                  >
                    <span className={`gate-mark ${gate.status}`}>
                      <Clock3 size={14} />
                    </span>
                    <span>
                      <strong>{memory.topics[gate.topic]}</strong>
                      <small>
                        {gate.id} · {gate.owner || "Référent non précisé"}
                      </small>
                      <b>{STATES[gate.status]}</b>
                    </span>
                    <ChevronRight size={15} />
                  </button>
                ))}
              </div>
              {!memory.gates.length && (
                <p>Aucune condition ouverte extraite.</p>
              )}
            </section>
            <OwnerHistory memory={memory} onSelect={setSelection} />
            <section className="insight-card">
              <span className="memory-eyebrow">
                <GitBranch size={15} /> ÉVOLUTION DE LA CIBLE
              </span>
              <div className="target-history">
                {memory.schedule.changes.map((change, index) => (
                  <button
                    key={`${change.date}-${change.target}`}
                    onClick={() =>
                      setSelection({
                        ...change,
                        title: `Cible : ${formatDate(change.target, { day: "numeric", month: "long" })}`,
                        summary: `Décision documentée le ${change.date}. ${change.conditional_evidence ? "Des conditions de go-live ont ensuite été rappelées." : ""}`,
                        evidence: [
                          ...change.evidence,
                          ...(change.conditional_evidence || []),
                        ],
                      })
                    }
                  >
                    <span
                      className={`history-node ${index === memory.schedule.changes.length - 1 ? "current" : ""}`}
                    />
                    <span>
                      <strong>
                        {formatDate(change.target, {
                          day: "numeric",
                          month: "long",
                        })}
                      </strong>
                      <small>
                        {index === 0
                          ? "Cible initiale"
                          : "Nouvelle cible approuvée"}{" "}
                        · {formatDate(change.date)}
                      </small>
                    </span>
                    <ArrowRight size={14} />
                  </button>
                ))}
              </div>
              <p className="insight-footnote">
                Une proposition fournisseur ne remplace pas une décision du
                comité.
              </p>
            </section>
            <section className="insight-card attention-card">
              <span className="memory-eyebrow">
                <TriangleAlert size={15} /> POINTS DE VIGILANCE
              </span>
              {memory.alerts.map((alert) => (
                <button
                  key={alert.id}
                  className="insight-alert"
                  onClick={() =>
                    setSelection({ ...alert, summary: alert.description })
                  }
                >
                  <strong>{alert.title}</strong>
                  <p>{alert.description}</p>
                  <span>
                    Comparer les sources <ArrowRight size={13} />
                  </span>
                </button>
              ))}
              {!memory.alerts.length && (
                <p className="muted">
                  Aucun écart détecté par les règles locales.
                </p>
              )}
            </section>
            <div className="memory-assurance">
              <ShieldCheck size={17} />
              <p>
                Des preuves, à chaque étape.
                <span>
                  Dates explicites. Auteurs identifiés. Incertitudes conservées.
                </span>
              </p>
            </div>
          </aside>
        )}
      </div>
      <footer className="memory-bottom">
        <span>
          <Sparkles size={14} /> Analyse locale · {memory.stats.documents}{" "}
          documents pertinents · dernière analyse{" "}
          {new Date(memory.generated_at).toLocaleString("fr-CA")}
        </span>
        <button
          className="text-button"
          onClick={() =>
            download(
              "nova-chronologie.json",
              JSON.stringify(events, null, 2),
              "application/json",
            )
          }
        >
          Exporter les données <Download size={14} />
        </button>
      </footer>
      {selection && <SourceDrawer selection={selection} close={closeDrawer} />}
    </div>
  );
}
