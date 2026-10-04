"""Resolve relative weeks in the user's timezone and select dated observations."""
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .intelligence import dates_in, fold

TIMEZONE = "America/Toronto"


def is_recent_changes_question(question):
    value = fold(question)
    return bool(re.search(r"chang|evolu|nouveaut|nouveau|what.*new|updates?", value)
                and re.search(r"semaine derniere|derniere semaine|last week|past week|7 derniers jours|sept derniers jours|last 7 days|past 7 days", value))


def week_window(question, today=None):
    end = today or datetime.now(ZoneInfo(TIMEZONE)).date()
    value = fold(question)
    # "Since last week" means a rolling seven-day lookback. A question strictly
    # about "last week" means the previous Monday through Sunday.
    calendar_week = not re.search(r"depuis|since|past|derniers jours|last 7 days", value)
    if calendar_week:
        this_monday = end - timedelta(days=end.weekday())
        return this_monday - timedelta(days=7), this_monday - timedelta(days=1)
    return end - timedelta(days=7), end


def _in_window_text(summary, event_date, start):
    sentences = re.split(r"(?<=[.!?])\s+", summary)
    selected = []
    for sentence in sentences:
        dates = dates_in(sentence, event_date.year)
        # A new publication repeating an older event does not redate that event.
        if dates and all(item["date"] < start.isoformat() for item in dates):
            continue
        selected.append(sentence)
    return " ".join(selected).strip()


def recent_updates(memory, question, today=None):
    start, end = week_window(question, today)
    updates, seen = [], set()
    for event in memory.get("events", []):
        if event.get("date_kind") not in {"observed", "effective"}:
            continue
        try:
            on = date.fromisoformat(event.get("date") or "")
        except ValueError:
            continue
        if not start <= on <= end:
            continue
        evidence = [item for item in event.get("evidence", [])
                    if item.get("path") and not item["path"].startswith("08_Archives")
                    and item["path"] not in {"README.txt", "MANIFEST.csv"}]
        # Register and plan snapshots show state at publication, not the date
        # when each underlying risk, completion, or planned activity changed.
        if not evidence or all(item["path"].endswith((".xlsx", ".csv")) for item in evidence):
            continue
        text = _in_window_text(event.get("summary", ""), on, start)
        if not text:
            continue
        value = fold(text)
        reminder = bool(re.search(r"toujours|encore|reste|demeure|rappel|maintenu|pas approuve|n.est pas approuve", value))
        action = bool(re.search(r"conditions concretes|trois conditions|fait partie des conditions|publie|precise|annonce|on vise|nouveau|decid|approuv|reportons|reporte|deploye|livre|ferme|je ferme|reprend|cree", value))
        section = "updates" if action and not reminder else "followups"
        key = (on.isoformat(), fold(text))
        if key in seen:
            continue
        seen.add(key)
        updates.append({"date": on.isoformat(), "text": text, "section": section,
                        "topic": event.get("topic"), "evidence": evidence})
    updates.sort(key=lambda item: (item["date"], item["section"], item["text"]))
    return {"start": start.isoformat(), "end": end.isoformat(), "timezone": TIMEZONE,
            "corpus_as_of": memory.get("as_of"), "updates": updates}
