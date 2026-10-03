"""Evidence-first, offline temporal extraction. No model or API key is required.

Publication dates, effective dates and planning dates have different meanings.
Only explicit source statements establish approval or completion. Source excerpts
and locators travel with every extracted event; undated items stay undated.
"""
import hashlib
import json
import re
import unicodedata
from collections import Counter
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
MONTHS = {"janvier": 1, "janv": 1, "fevrier": 2, "fevr": 2, "mars": 3,
          "avril": 4, "avr": 4, "mai": 5, "juin": 6, "juillet": 7,
          "juil": 7, "aout": 8, "septembre": 9, "sept": 9,
          "octobre": 10, "oct": 10, "novembre": 11, "nov": 11,
          "decembre": 12, "dec": 12}
DATE_PATTERN = re.compile(r"\b(?:(\d{4})-(\d{2})-(\d{2})|(\d{1,2})[/.](\d{1,2})[/.](\d{4})|(\d{1,2})(?:er)?\s+(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\.?(?:\s+(\d{4}))?)\b")
TOPICS = {"schedule": "Échéancier", "security": "Sécurité", "accessibility": "Accessibilité",
          "operations": "Exploitation", "integration": "Intégration", "data": "Données",
          "performance": "Performance", "architecture": "Architecture", "scope": "Portée",
          "finance": "Finances", "governance": "Gouvernance", "delivery": "Livraison"}


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def dates_in(text, year=None):
    """Parse explicit dates, inheriting a year only from dated source context."""
    found = []
    for match in DATE_PATTERN.finditer(fold(text)):
        y, mo, day, d2, m2, y2, d3, m3, y3 = match.groups()
        if d3 and not (y3 or year):
            continue
        try:
            value = date(int(y or y2 or y3 or year), int(mo or m2 or MONTHS.get(m3, 0)), int(day or d2 or d3)).isoformat()
        except ValueError:
            continue
        found.append({"date": value, "start": match.start(), "end": match.end(), "text": text[match.start():match.end()]})
    return found


def source_date(doc):
    text = doc["text"]
    if doc["extension"] == ".eml":
        match = re.search(r"^Date:\s*(.+)$", text, re.M)
        if match:
            try:
                return parsedate_to_datetime(match[1]).date().isoformat()
            except (TypeError, ValueError):
                pass
    # Versioned spreadsheets carry publication dates, not activity start dates.
    filename = fold(Path(doc["path"]).stem)
    stamp = re.search(r"(\d{1,2})(janv|fevr|mars|avr|mai|juin|juil|aout|sept|oct|nov|dec)", filename)
    if stamp:
        years = re.findall(r"\b(20\d{2})\b", text)
        if years:
            return date(int(years[0]), MONTHS[stamp[2]], int(stamp[1])).isoformat()
    lines = text.splitlines()
    for number, line in enumerate(lines):
        normalized = fold(line).strip().strip("*# ")
        metadata = re.match(r"^(?:date(?: de decision)?|cree|demande initiale)(?:\s*[:*]|\s*$)", normalized)
        dated_header = number < 8 and (re.match(r"^\d{1,2}\s+\w+\s+20\d{2}", normalized) or re.search(r"comite|suivi livraison|architecture nova|rapport de statut", normalized))
        if metadata or dated_header:
            matches = dates_in(line)
            if not matches and metadata and number + 1 < len(lines):
                matches = dates_in(lines[number + 1])
            if matches:
                return matches[0]["date"]
    # Timestamped logs are observations, not planning documents.
    if "logs" in doc["path"]:
        matches = dates_in(text)
        if matches:
            return matches[0]["date"]
    return None


def topic_of(text):
    value = fold(text)
    for key, words in (
        ("security", ("sec-", "securite", "journalisation", "audit admin")),
        ("accessibility", ("acc-", "accessibilite", "contraste", "nvda", "clavier", "labels")),
        ("operations", ("ops-", "runbook", "rollback", "exploitation")),
        ("integration", ("int-", "connecteur", "integration")),
        ("data", ("data-", "doublon", "idempotence", "migration donnees")),
        ("performance", ("perf-", "performance", "620 ms", "scan complet")),
        ("scope", ("cr-04", "mobile", "portee", "phase 2")),
        ("finance", ("inv-", "facture", "budget", "cr-01", "contractuel")),
        ("architecture", ("canada central", "east us", "architecture", "hebergement", "sso")),
        ("governance", ("charge du projet", "chargee de projet", "charge de projet", "transition", "reprend officiellement")),
        ("schedule", ("octobre", "go-live", "echeancier", "date cible", "mise en production")),
    ):
        if any(word in value for word in words):
            return key
    return "delivery"


def classify(text):
    value = fold(text)
    if any(term in value for term in ("brouillon", "proposition", "recommandation", "recommandons")):
        return "proposal", "proposed"
    if re.search(r"(?:non|pas|jamais|aucune?)\s+(?:\w+\s+){0,3}appro\w*|approbation requise|sans (?:nouvelle )?approbation|n['’]est pas approuve", value):
        return "decision", "not_approved"
    if any(term in value for term in ("conditionnel", "sous reserve", "conditions de go-live")):
        return "decision", "conditional"
    if any(term in value for term in ("approuve", "acceptee", "decision", "on tranche", "reportons", "ne font pas partie")):
        return "decision", "approved"
    if any(term in value for term in ("ne pas fermer", "en validation", "re-test planifie", "validation restera requise", "avant validation", "jusqu'a notre re-test")):
        return "validation", "in_review"
    if any(term in value for term in ("ferme", "je ferme", "valide", "re-test ok", "aucun doublon", "120/120")):
        return "validation", "completed"
    if any(term in value for term in ("bloquant", "toujours ouvert", "incomplet", "pas pret", "risque", "manque", "retard", "401 unauthorized")):
        return "risk", "open"
    if any(term in value for term in ("deploye", "livre", "correctif", "corrige", "migration", "index ajoute")):
        return "delivery", "delivered"
    return "update", "reported"


def clean(text):
    return re.sub(r"\s+", " ", text).strip(" -\n")


def roster_from(documents):
    roster = set()
    for doc in documents:
        for match in re.finditer(r"^(?:From|Demandeur|Chargée? de projet|Responsable)\s*:\s*([^\n<]+)", doc["text"], re.M | re.I):
            name = match[1].strip()
            if 2 <= len(name.split()) <= 3 and "@" not in name and len(name) < 45:
                roster.add(name)
        for match in re.finditer(r"^Participants\s*:\s*(.+)$", doc["text"], re.M | re.I):
            for item in match[1].split(","):
                name = re.sub(r"\s*\(.*?\)", "", item).strip()
                if len(name.split()) == 2 and "représentant" not in name.lower():
                    roster.add(name)
    return {fold(name.split()[0]): name for name in sorted(roster)}


def resolve_owner(name, roster):
    name = re.sub(r"\s*\(.*?\)", "", name).strip()
    return roster.get(fold(name), name) if name else None


def evidence(doc, excerpt, locator):
    return {"document_id": doc["id"], "path": doc["path"], "locator": locator,
            "excerpt": excerpt.strip(), "published_on": source_date(doc)}


def event(doc, on, title, summary, locator, owner=None, owner_role=None, kind=None, status=None, topic=None, date_kind="observed", end_date=None):
    detected_kind, detected_status = classify(summary)
    return {"date": on, "end_date": end_date, "date_kind": date_kind,
            "title": clean(title)[:150], "summary": clean(summary),
            "type": kind or detected_kind, "status": status or detected_status,
            "topic": topic or topic_of(summary), "owner": owner, "owner_role": owner_role,
            "evidence": [evidence(doc, summary, locator)], "confidence": "explicit",
            "sources": [doc["path"]]}


def extract_ticket(doc, roster):
    text = doc["text"]
    ticket = re.search(r"TICKET\s+([A-Z]+-\d+)", text)
    if not ticket:
        return [], None
    ticket_id = ticket[1]
    title = re.search(r"^Titre\s*:\s*(.+)$", text, re.M)
    status = re.search(r"^Statut\s*:\s*(.+)$", text, re.M)
    requester = re.search(r"^Demandeur\s*:\s*(.+)$", text, re.M)
    created = source_date(doc)
    owner = resolve_owner(requester[1], roster) if requester else None
    state = fold(status[1]) if status else ""
    state = "completed" if "ferme" in state else "in_review" if "validation" in state else "open"
    topic = topic_of(ticket_id)
    label = clean(title[1]) if title else ticket_id
    events = [event(doc, created, f"{ticket_id} · Signalement", text.split("Commentaires")[0].strip(), "En-tête du ticket", owner, "Demandeur", "risk", "open", topic)]
    description = re.search(r"(?:Description initiale|Description|Contexte)\s*:\s*([^\n]+)", text)
    events[0]["summary"] = f"{label}. " + (clean(description[1]) if description else "Signalement documenté dans le ticket.")
    year = int(created[:4]) if created else None
    for number, line in enumerate(text.splitlines(), 1):
        dated = dates_in(line, year)
        if not dated or not re.match(r"^\s*(?:\d{1,2}\s|Validation\s*:)", line):
            continue
        author = re.search(r"\s[-–]\s*([^:]+):", line)
        speaker = resolve_owner(author[1], roster) if author else owner
        kind, item_state = classify(line)
        events.append(event(doc, dated[0]["date"], f"{ticket_id} · {clean(line[dated[0]['end']:]).lstrip(' -')[:95]}", line, f"Ligne {number}", speaker, "Intervenant" if author else "Demandeur", kind, item_state, topic))
    completed_dates = [e["date"] for e in events[1:] if e["status"] == "completed"]
    record = {"id": ticket_id, "title": label, "topic": topic, "owner": owner,
              "owner_role": "Demandeur", "status": state, "created_on": created,
              "completed_on": max(completed_dates) if completed_dates and state == "completed" else None,
              "last_update": max((e["date"] for e in events if e["date"]), default=created),
              "evidence": [evidence(doc, text, "Ticket complet")],
              "event_ids": []}
    return events, record


def extract_plan(doc):
    events, phases = [], []
    headers = None
    for line_number, line in enumerate(doc["text"].splitlines(), 1):
        columns = [item.strip() for item in line.split("|")]
        if columns[0] == "ID":
            headers = columns
            continue
        if not headers or not re.fullmatch(r"P-\d+", columns[0]):
            continue
        fields = dict(zip(headers, columns))
        start = fields.get("Début planifié", fields.get("Début"))
        end = fields.get("Fin planifiée", fields.get("Fin"))
        if not dates_in(start or "") or not dates_in(end or ""):
            continue
        state = fold(fields.get("Statut", ""))
        status = "completed" if "termine" in state else "in_progress" if "en cours" in state else "planned"
        owner = fields.get("Responsable")
        activity = fields.get("Activité", columns[0])
        item = event(doc, start, activity, line, f"Plan projet · ligne {line_number}", owner, "Responsable du plan", "milestone", status, topic_of(activity), "planned", end)
        item["plan_id"] = columns[0]
        events.append(item)
        phases.append({"id": columns[0], "title": activity, "start": start, "end": end,
                       "status": status, "owner": owner, "evidence": item["evidence"]})
    return events, phases


def extract_document(doc, roster):
    text = doc["text"]
    on = source_date(doc)
    events = []
    if not on:
        return events
    lines = [(i, line.strip()) for i, line in enumerate(text.splitlines(), 1) if line.strip()]
    title = re.sub(r"[_-]+", " ", Path(doc["path"]).stem)
    if doc["extension"] == ".eml":
        subject = re.search(r"^Subject:\s*(.+)$", text, re.M)
        sender = re.search(r"^From:\s*([^<\n]+)", text, re.M)
        body_lines = [line for _, line in lines if not re.match(r"^(Subject|From|To|Date):|^>", line)]
        body = "\n".join(body_lines)
        events.append(event(doc, on, subject[1] if subject else title, body, "Corps du courriel",
                            sender[1].strip() if sender else None, "Auteur"))
    elif "03_Tickets/" not in doc["path"]:
        year = int(on[:4])
        if "Transcript" in doc["path"] or "Teams_" in doc["path"]:
            for number, line in lines:
                speaker = re.match(r"(\d{2}:\d{2})(?:\s*[-–])?\s+([^:]+):\s*(.+)", line)
                if not speaker:
                    continue
                content = speaker[3]
                if not re.search(r"appro|valid|correct|bloqu|Canada Central|SSO|runbook|rollback|fermé|ferme|condition|report|phase|octobre|charge|reprend|journalis|chemin critique|CR-", content, re.I):
                    continue
                events.append(event(doc, on, clean(content)[:105], line, f"{speaker[1]} · ligne {number}", resolve_owner(speaker[2], roster), "Intervenant"))
        else:
            # Keep document-level context intact, particularly negations and conditions.
            events.append(event(doc, on, title, text, "Document" if doc["extension"] != ".pdf" else "Page 1"))
    return events


def extract_risks(doc):
    headers, events = None, []
    for number, line in enumerate(doc["text"].splitlines(), 1):
        columns = [part.strip() for part in line.split("|")]
        if columns[0] == "ID":
            headers = columns
        elif headers and re.fullmatch(r"R-\d+", columns[0]):
            fields = dict(zip(headers, columns))
            events.append(event(doc, source_date(doc), f"{columns[0]} · {fields.get('Risque', 'Risque documenté')}", line,
                                f"Registre Risques · ligne extraite {number}", fields.get("Propriétaire"), "Propriétaire du risque", "risk",
                                "completed" if "ferme" in fold(fields.get("Statut", "")) else "open", topic_of(line)))
    return events


def extract_assignments(documents, roster):
    assignments = {}
    for doc in documents:
        on = source_date(doc)
        if not on:
            continue
        text = doc["text"]
        matches = re.findall(r"Chargée? de projet\s*:\s*([^\n]+)", text, re.I)
        for name in set(roster.values()):
            if re.search(re.escape(name) + r"\s+(?:prend|reprend|agit)\b[^\n.]{0,65}(?:charge|chargé|rôle)", text, re.I):
                matches.append(name)
        for name in matches:
            name = resolve_owner(name, roster)
            key = (on, name)
            proof = evidence(doc, text, "Attribution explicite de la charge de projet")
            if key in assignments:
                assignments[key]["evidence"].append(proof)
            else:
                assignments[key] = {"owner": name, "role": "Charge de projet", "effective_on": on, "until": None, "evidence": [proof]}
    ordered = sorted(assignments.values(), key=lambda item: item["effective_on"])
    for index, item in enumerate(ordered[:-1]):
        item["until"] = ordered[index + 1]["effective_on"]
    return ordered


def schedule_history(documents):
    """Extract governance assertions; a stale plan cannot override a decision."""
    history = []
    for doc in documents:
        if "08_Archives" in doc["path"] or doc["extension"] == ".xlsx":
            continue
        text, on = doc["text"], source_date(doc)
        if not on:
            continue
        lower = fold(text)
        year = int(on[:4])
        candidates = [d for d in dates_in(text, year) if d["date"] > on and "oct" in fold(d["text"])]
        if not candidates or not any(w in lower for w in ("production", "lancement", "date officielle", "cible approuvee")):
            continue
        # Prefer the last target if a source explicitly moves the original date.
        target = candidates[-1]["date"]
        approved = "approuve" in lower or "charte" in lower or "confirme le demarrage" in lower
        explicit_decision = bool(re.search(r"donc\W+approuve|date officielle|date cible[^\n]+est deplacee", lower))
        proposed = ("proposition" in lower or "recommandation" in lower) and not explicit_decision
        stale = "brouillon" in fold(Path(doc["path"]).stem) or "rapport_statut" in fold(doc["path"])
        state = "proposed" if proposed else "approved" if approved and not stale else "reported"
        conditional = "conditionnel" in lower or "pas un go automatique" in lower or "sous reserve" in lower
        history.append({"date": on, "target": target, "status": "conditional" if conditional and state == "approved" else state,
                        "evidence": [evidence(doc, text, "Date cible et décision")],
                        "title": "Cible conditionnelle" if conditional and state == "approved" else "Cible approuvée" if state == "approved" else "Report proposé" if proposed else "Date mentionnée"})
    history.sort(key=lambda item: item["date"])
    return history


def build_project_memory(documents):
    relevant = [d for d in documents if not d["path"].startswith("08_Archives") and d["path"] not in ("README.txt", "MANIFEST.csv") and not d["text"].startswith("Extraction failed:")]
    roster = roster_from(relevant)
    assignments = extract_assignments(relevant, roster)
    events, tickets, plans, undated = [], [], [], []
    for doc in relevant:
        if doc["extension"] == ".xlsx":
            if "Plan_" in doc["path"]:
                plan_events, phases = extract_plan(doc)
                plans.append((doc["path"], plan_events, phases))
            elif "Risques" in doc["path"]:
                events.extend(extract_risks(doc))
            continue
        ticket_events, ticket = extract_ticket(doc, roster)
        if ticket:
            events.extend(ticket_events)
            tickets.append(ticket)
        else:
            extracted = extract_document(doc, roster)
            events.extend(extracted)
            if not extracted and not source_date(doc):
                undated.append({"id": doc["id"], "path": doc["path"], "reason": "Aucune date de publication explicite"})
    # Latest plan version only; historical documents remain available as evidence.
    plans.sort(key=lambda p: p[0])
    phases = plans[-1][2] if plans else []
    # References to earlier targets belong to decision history, not live agenda.
    events = [e for e in events if e["date_kind"] != "planned"]
    history = schedule_history(relevant)
    authoritative = [h for h in history if h["status"] in ("approved", "conditional")]
    target = authoritative[-1]["target"] if authoritative else None
    if plans:
        for planned in plans[-1][1]:
            if planned["topic"] == "schedule" and target and planned["date"] != target:
                planned["status"] = "superseded"
            events.append(planned)
    if authoritative:
        current = authoritative[-1]
        target_doc = next(d for d in relevant if d["id"] == current["evidence"][0]["document_id"])
        milestone = event(target_doc, target, "Mise en production NOVA", current["evidence"][0]["excerpt"],
                          "Cible approuvée dans la dernière décision", kind="milestone", status=current["status"], topic="schedule", date_kind="planned")
        milestone["evidence"] = current["evidence"]
        milestone["summary"] = f"La cible approuvée de mise en production est le {target}. " + (
            "Elle reste conditionnelle aux validations explicitement citées dans la dernière source."
            if current["status"] == "conditional" else "Cette date provient d’une source de gouvernance explicite.")
        responsible = [a for a in assignments if a["effective_on"] <= current["date"]]
        if responsible:
            milestone["owner"] = responsible[-1]["owner"]
            milestone["owner_role"] = "Charge de projet"
            milestone["evidence"] = milestone["evidence"] + responsible[-1]["evidence"]
        events.append(milestone)
    unique = {}
    for item in events:
        signature = f"{item['date']}|{item['date_kind']}|{fold(item['title'])}|{fold(item['summary'])}"
        item["id"] = "evt-" + hashlib.sha256(signature.encode()).hexdigest()[:12]
        if item["id"] in unique:
            existing = unique[item["id"]]
            existing["evidence"].extend(item["evidence"])
            existing["sources"].extend(item["sources"])
        else:
            unique[item["id"]] = item
    events = sorted(unique.values(), key=lambda e: (e["date"] or "9999", e["date_kind"], e["id"]))
    for ticket in tickets:
        ticket["event_ids"] = [e["id"] for e in events if e["title"].startswith(ticket["id"])]
    observed = [e["date"] for e in events if e["date"] and e["date_kind"] == "observed"]
    as_of = max(observed) if observed else None
    changes = []
    for item in authoritative:
        if not changes or item["target"] != changes[-1]["target"]:
            changes.append(item)
        elif item["status"] == "conditional":
            changes[-1]["conditional_evidence"] = item["evidence"]
    gates = [t for t in tickets if t["topic"] in ("security", "accessibility", "operations") and t["status"] != "completed"]
    alerts = []
    for phase in phases:
        if topic_of(phase["title"]) == "schedule" and target and phase["end"] != target:
            alerts.append({"id": "stale-plan", "title": "Le plan contient une ancienne date", "description": f"Le plan indique le {phase['end']}, alors que la cible approuvée est le {target}. La décision de gouvernance prévaut.", "evidence": phase["evidence"] + authoritative[-1]["evidence"]})
            phase["warning"] = f"Date périmée · cible approuvée : {target}"
    if gates:
        alerts.append({"id": "pending-gates", "title": "Le go-live reste conditionnel", "description": f"{len(gates)} tickets de sécurité, d’accessibilité ou d’exploitation restent ouverts ou en validation. Une livraison fournisseur ne constitue pas une acceptation.", "evidence": [ev for t in gates for ev in t["evidence"]]})
    reports = [d for d in relevant if "Rapport_Statut" in d["path"] and "VERT" in d["text"]]
    if reports and gates:
        alerts.append({"id": "status-conflict", "title": "Un statut « vert » contredit les validations restantes", "description": "Le rapport de statut présente des volets comme terminés ; les tickets et le comité ultérieurs maintiennent des conditions ouvertes.", "evidence": [evidence(reports[0], reports[0]["text"], "Page 1")] + [ev for t in gates for ev in t["evidence"]]})
    registers = [d for d in relevant if "Registre_Risques" in d["path"]]
    resolved_integration = [t for t in tickets if t["topic"] == "integration" and t["status"] == "completed"]
    if registers and resolved_integration:
        stale_rows = [line for line in registers[-1]["text"].splitlines() if "connecteur" in fold(line) and "ouvert" in fold(line)]
        if stale_rows:
            alerts.append({"id": "stale-risk", "title": "Un risque clos reste ouvert dans le registre", "description": "Le registre conserve le risque du connecteur ouvert, alors que le ticket d’intégration atteste sa fermeture. Vérifier la date de suivi de la ligne.", "evidence": [evidence(registers[-1], stale_rows[0], "Ligne du risque connecteur")] + resolved_integration[0]["evidence"]})
    completed = [t for t in tickets if t["status"] == "completed"]
    series = []
    for day in sorted(set(observed)):
        created = sum(bool(t["created_on"] and t["created_on"] <= day) for t in tickets)
        closed = sum(bool(t["completed_on"] and t["completed_on"] <= day) for t in tickets)
        series.append({"date": day, "created": created, "closed": closed, "open": created - closed})
    owners = Counter(e["owner"] for e in events if e["owner"])
    return {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
            "as_of": as_of, "extraction": {"mode": "local-evidence", "label": "Extraction locale fondée sur les sources", "description": "Dates explicites, champs structurés et règles linguistiques. L’extraction de base ne dépend pas d’un LLM. Les référents et auteurs ne sont pas assimilés à des responsables assignés.", "excluded_documents": len(documents) - len(relevant), "undated_documents": undated},
            "events": events, "tickets": tickets, "phases": phases, "assignments": assignments,
            "schedule": {"current_target": target, "history": history, "changes": changes,
                         "conditional": bool(gates) or bool(authoritative and authoritative[-1]["status"] == "conditional"),
                         "delay_days": (date.fromisoformat(target) - date.fromisoformat(changes[0]["target"])).days if target and changes else 0},
            "gates": gates, "alerts": alerts, "progress": series,
            "owners": [{"name": name, "events": count} for name, count in sorted(owners.items())],
            "topics": TOPICS, "stats": {"documents": len(relevant), "events": len(events),
                "decisions": sum(e["type"] == "decision" for e in events if e["date_kind"] == "observed"),
                "owners": len(owners), "tickets": len(tickets), "completed_tickets": len(completed),
                "open_tickets": len(tickets) - len(completed), "gates": len(gates)}}


def save_project_memory(memory):
    PROCESSED.mkdir(parents=True, exist_ok=True)
    for name, value in (("project_memory.json", memory), ("timeline.json", memory["events"])):
        temporary = PROCESSED / (name + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(PROCESSED / name)


def get_project_memory():
    path = PROCESSED / "project_memory.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    docs_path = PROCESSED / "documents.json"
    docs = json.loads(docs_path.read_text(encoding="utf-8")) if docs_path.exists() else []
    memory = build_project_memory(docs)
    save_project_memory(memory)
    return memory
