"""Durable source imports and evidence-backed before/after impact reports."""
import hashlib
import json
from pathlib import Path
import re
import shutil
from datetime import date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from . import ingest
from .intelligence import build_project_memory, classify, source_date, topic_of
from .synthesis import build_synthesis

STORE = ingest.ROOT / "data" / "updates"
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TEXT_CHARS = 250_000
STATES = {"completed": "fermé / accepté", "open": "ouvert", "in_review": "en validation",
          "approved": "approuvé", "conditional": "conditionnel", "proposed": "proposé",
          "not_approved": "non approuvé", "reported": "information reçue", "delivered": "livraison annoncée"}


def _read(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _token(value):
    if not re.fullmatch(r"[a-f0-9]{32}", value):
        raise ValueError("Identifiant d'import invalide.")
    return value


def _current():
    documents = _read(ingest.PROCESSED / "documents.json", [])
    memory = _read(ingest.PROCESSED / "project_memory.json", None)
    return documents, memory if memory is not None and memory.get('calendar_extraction_version') == 2 else build_project_memory(documents)


def _draft(record, reviewed_text=None, document_date=None):
    text = record["extracted_text"] if reviewed_text is None else reviewed_text
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError("Le texte extrait dépasse la limite de 250 000 caractères.")
    if document_date:
        try:
            document_date = date.fromisoformat(document_date).isoformat()
        except ValueError:
            raise ValueError("La date du document doit être au format AAAA-MM-JJ.") from None
    path = f"09_Mises_a_jour/{record['id']}/{record['filename']}"
    return {"id": "doc-" + hashlib.sha256(path.encode()).hexdigest()[:16], "path": path,
            "title": Path(record["filename"]).stem.replace("_", " "),
            "extension": Path(record["filename"]).suffix.lower(), "text": text,
            "summary": ingest.normalize_space(text)[:260], "tags": ingest.infer_tags(path, text),
            "imported_at": record["received_at"], "source_date_override": document_date,
            "original_name": record["filename"], "content_sha256": record["content_sha256"],
            "text_reviewed": text != record["extracted_text"]}


def impact_report(document, before_documents, before, after):
    identifier = document["id"]
    imported_events = [item for item in after["events"]
                       if any(proof["document_id"] == identifier for proof in item["evidence"])]
    changes, actions = [], []
    previous_target, target = before["schedule"]["current_target"], after["schedule"]["current_target"]
    if target != previous_target:
        changes.append({"title": "Cible approuvée de mise en production", "before": previous_target or "Non précisée",
                        "after": target or "Non précisée", "kind": "confirmed",
                        "evidence": [proof for item in imported_events for proof in item["evidence"] if proof["document_id"] == identifier]})
        actions.append("Mettre à jour les plans et communications avec la nouvelle cible approuvée, en conservant les anciennes décisions.")
    prior_tickets = {ticket["id"]: ticket for ticket in before["tickets"]}
    for ticket in after["tickets"]:
        previous = prior_tickets.get(ticket["id"])
        if (previous or {}).get("status") != ticket["status"]:
            changes.append({"title": ticket["id"] + " · " + ticket["title"], "before": STATES.get((previous or {}).get("status"), "Non documenté"),
                            "after": STATES.get(ticket["status"], ticket["status"]), "kind": "confirmed", "evidence": ticket["evidence"]})
            actions.append(f"Actualiser le suivi de {ticket['id']} avec cette preuve; ne pas étendre cette conclusion aux autres tickets.")
    assertions = [item for item in after["schedule"]["history"]
                  if any(proof["document_id"] == identifier for proof in item["evidence"])]
    for assertion in assertions:
        if assertion["status"] in {"proposed", "reported"}:
            changes.append({"title": "Nouvelle date proposée ou mentionnée", "before": previous_target or "Non précisée",
                            "after": assertion["target"] + " — " + STATES.get(assertion["status"], "à confirmer"),
                            "kind": "proposal", "evidence": assertion["evidence"]})
            actions.append(f"Obtenir une décision explicite avant de remplacer la cible approuvée ({target or 'non précisée'}).")
    if not changes:
        kind, state = classify(document["text"])
        changes.append({"title": "Nouvelle pièce documentaire", "before": "Absente du corpus",
                        "after": document["original_name"] + " — " + STATES.get(state, "information reçue"),
                        "kind": "proposal" if kind == "proposal" else "information", "evidence": [
                            {"document_id": identifier, "path": document["path"], "locator": "Document importé",
                             "published_on": source_date(document), "excerpt": document["text"][:1200]}]})

    # Only explicit identifiers or an actual approved schedule change establish impact.
    references = set(re.findall(r"\b[A-Z]{2,}-\d+\b", document["text"]))
    affected = []
    selected_events = set()
    for ticket in before["tickets"]:
        if ticket["id"] not in references:
            continue
        candidates = [e for e in before["events"] if e["id"] in ticket.get("event_ids", [])]
        if not candidates:
            continue
        latest = max(candidates, key=lambda e: e.get("date") or "")
        selected_events.update(e["id"] for e in candidates)
        affected.append({"id": ticket["id"], "title": ticket["id"] + " ? " + ticket["title"],
                         "event_id": latest["id"], "date": latest.get("date"), "kind": "task"})
    for old_event in before["events"]:
        if old_event["id"] in selected_events:
            continue
        explicit = references.intersection(re.findall(r"\b[A-Z]{2,}-\d+\b", old_event["title"]))
        schedule_affected = (target != previous_target or any(a["target"] != previous_target for a in assertions)) and old_event.get("date_kind") == "planned" and old_event.get("date") == previous_target and old_event.get("topic") == "schedule"
        if explicit or schedule_affected:
            destination = next((e for e in after["events"] if e["id"] == old_event["id"]), None)
            if destination is None and schedule_affected:
                destination = next((e for e in after["events"] if e["title"] == old_event["title"] and e.get("date_kind") == "planned"), None)
            destination = destination or old_event
            affected.append({"id": old_event["id"], "title": old_event["title"],
                             "event_id": destination["id"], "date": destination.get("date"), "kind": "event",
                             "previous_event_id": old_event["id"]})
    for action in build_synthesis([document], after)["groups"]["engagements"]:
        if any(proof["document_id"] == identifier for proof in action["evidence"]):
            actions.append("Engagement mentionné dans la nouvelle source : " + action["title"])
    if not source_date(document):
        actions.append("Confirmer la date du document. Le calendrier indique sa réception, pas la date supposée du fait.")
    if after["gates"]:
        actions.append("Suivre séparément les conditions encore ouvertes : " + ", ".join(t["id"] for t in after["gates"]) + ".")
    if not actions:
        actions.append("Recouper la nouvelle information avec les sources liées avant de modifier une décision ou une validation.")
    return {"summary": "Nouvelle source analysée avec comparaison à l'état précédent.",
            "changes": changes, "affected_information": affected, "actions": list(dict.fromkeys(actions)),
            "previous_target": previous_target, "current_target": target,
            "remaining_gates": [ticket["id"] for ticket in after["gates"]],
            "events": [{key: item[key] for key in ("id", "title", "date", "date_kind", "status", "summary")} for item in imported_events],
            "document": {key: document.get(key) for key in ("id", "path", "title", "original_name", "source_date_override", "imported_at", "text_reviewed")},
            "source_date": source_date(document),
            "notice": "Les sources précédentes sont conservées. Les propositions, livraisons et validations restent distinctes."}


def preview_upload(filename, content):
    filename = Path((filename or "").replace("\\", "/")).name
    filename = re.sub(r"[^\w .()\-]", "_", filename)[:180]
    suffix = Path(filename).suffix.lower()
    if not filename or filename.startswith((".", "~$")) or suffix not in ingest.READERS:
        raise ValueError("Format accepté : EML, TXT, MD, CSV, XLSX, PDF, PNG, JPG, JPEG ou WEBP.")
    if not content or len(content) > MAX_FILE_BYTES:
        raise ValueError("Le fichier doit être non vide et ne pas dépasser 20 Mo.")
    digest = hashlib.sha256(content).hexdigest()
    with ingest.INGEST_LOCK:
        documents, _ = _current()
        if any(doc.get("content_sha256") == digest for doc in documents):
            raise ValueError("Ce fichier est déjà présent dans le corpus; aucune copie supplémentaire n'a été ajoutée.")
    identifier = uuid4().hex
    folder = STORE / "pending" / identifier
    folder.mkdir(parents=True)
    source = folder / filename
    source.write_bytes(content)
    text, warnings = ingest.extract_source(source)
    record = {"id": identifier, "filename": filename, "size": len(content), "content_sha256": digest,
              "received_at": datetime.now(ZoneInfo("America/Toronto")).isoformat(),
              "extracted_text": text[:MAX_TEXT_CHARS], "warnings": warnings}
    if len(text) > MAX_TEXT_CHARS:
        record["warnings"].append("Texte limité à 250 000 caractères : vérifiez que les éléments utiles sont présents.")
    _write(folder / "record.json", record)
    report = analyze_upload(identifier)
    return {**record, "analysis": report, "detected_date": report["source_date"]}


def analyze_upload(identifier, reviewed_text=None, document_date=None):
    record = _read(STORE / "pending" / _token(identifier) / "record.json", None)
    if record is None:
        raise ValueError("Aperçu introuvable. Sélectionnez à nouveau le fichier.")
    document = _draft(record, reviewed_text, document_date)
    with ingest.INGEST_LOCK:
        documents, before = _current()
        after = build_project_memory([*documents, document])
        return impact_report(document, documents, before, after)


def integrate_upload(identifier, reviewed_text=None, document_date=None):
    identifier = _token(identifier)
    with ingest.INGEST_LOCK:
        completed = STORE / "history" / identifier / "result.json"
        if completed.exists():
            return _read(completed, {})
        record = _read(STORE / "pending" / identifier / "record.json", None)
        if record is None:
            raise ValueError("Aperçu introuvable. Sélectionnez à nouveau le fichier.")
        document = _draft(record, reviewed_text, document_date)
        if not document["text"].strip():
            raise ValueError("Ajoutez une transcription lisible avant d'intégrer ce fichier.")
        documents, before = _current()
        if any(doc.get("content_sha256") == record["content_sha256"] for doc in documents):
            raise ValueError("Ce fichier a déjà été intégré entre-temps.")
        source = STORE / "pending" / identifier / record["filename"]
        destination = ingest.DEFAULT_CORPUS / document["path"]
        destination.parent.mkdir(parents=True, exist_ok=False)
        history = completed.parent
        original_files = {name: (ingest.PROCESSED / name).read_bytes() if (ingest.PROCESSED / name).exists() else None
                          for name in ("documents.json", "chunks.json", "project_memory.json", "timeline.json")}
        try:
            shutil.copyfile(source, destination)
            _write(destination.with_name(destination.name + ".nova.json"), {
                "reviewed_text": document["text"], "original_name": record["filename"],
                "content_sha256": record["content_sha256"], "imported_at": record["received_at"],
                "source_date_override": document_date, "text_reviewed": document["text_reviewed"],
                "warnings": ["Transcription fournie ou corrigée lors de l'import."] if document["text_reviewed"] else record["warnings"]})
            after_documents, chunks, after = ingest.build_corpus(ingest.DEFAULT_CORPUS, documents)
            integrated = next(doc for doc in after_documents if doc["path"] == document["path"])
            report = impact_report(integrated, documents, before, after)
            result = {"id": identifier, "status": "integrated", "filename": record["filename"],
                      "integrated_at": datetime.now(ZoneInfo("America/Toronto")).isoformat(), "analysis": report}
            _write(history / "before.json", {"documents": documents, "memory": before})
            _write(history / "after.json", {"documents": after_documents, "memory": after})
            ingest.publish_corpus(after_documents, chunks, after)
            _write(completed, result)
        except Exception:
            for name, content in original_files.items():
                path = ingest.PROCESSED / name
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(content)
            shutil.rmtree(destination.parent)
            if history.exists():
                shutil.rmtree(history)
            raise
        return result


def history():
    with ingest.INGEST_LOCK:
        return sorted((_read(path, {}) for path in (STORE / "history").glob("*/result.json")),
                      key=lambda item: item["integrated_at"], reverse=True)


def remove_import(identifier, restore=False):
    identifier = _token(identifier)
    with ingest.INGEST_LOCK:
        result_path = STORE / 'history' / identifier / 'result.json'
        result = _read(result_path, None)
        if result is None:
            raise ValueError('Import introuvable.')
        relative = Path(result['analysis']['document']['path'])
        corpus = ingest.DEFAULT_CORPUS.resolve()
        source = (corpus / relative).resolve()
        if not source.is_relative_to(corpus / '09_Mises_a_jour') or not source.is_file():
            raise ValueError('Source importée introuvable.')
        metadata_path = source.with_name(source.name + '.nova.json')
        original_metadata = metadata_path.read_bytes()
        metadata = _read(metadata_path, {})
        metadata['import_removed'] = not restore
        documents, _ = _current()
        try:
            _write(metadata_path, metadata)
            rebuilt, chunks, memory = ingest.build_corpus(corpus, documents)
            updated = {**result, 'status': 'integrated' if restore else 'removed'}
            _write(result_path, updated)
            try:
                ingest.publish_corpus(rebuilt, chunks, memory)
            except Exception:
                _write(result_path, result)
                raise
        except Exception:
            metadata_path.write_bytes(original_metadata)
            raise
        return updated


def preview_file(identifier):
    folder = STORE / "pending" / _token(identifier)
    record = _read(folder / "record.json", None)
    if record is None:
        raise ValueError("Fichier d'aperçu introuvable.")
    return folder / record["filename"]
