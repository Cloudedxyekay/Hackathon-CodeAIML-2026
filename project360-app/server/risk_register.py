"""Read risk-register rows and reconcile explicitly dated closure evidence."""
import re

from .intelligence import dates_in, fold, source_date


def is_current_risk_question(question):
    value = fold(question)
    return bool(
        re.search(r"\b(risques|risks)\b", value)
        and re.search(r"quels|principaux|majeurs|aujourd|actuel|ouverts|top|main|current|today|what", value)
        and not re.search(r"\br-\d+\b|histor|etaient|fermes|clos|closed|resolved", value)
    )


def requested_count(question):
    value = fold(question)
    number = re.search(r"\b(\d+)\b", value)
    if number:
        return max(1, min(int(number[1]), 20))
    for word, count in {"un": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
                        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}.items():
        if re.search(rf"\b{word}\b", value):
            return count
    return 3 if re.search(r"principaux|majeurs|top|main", value) else None


def register_date(document):
    return source_date(document)


def parse_rows(document):
    """Support both normal spreadsheet text and older whitespace-flattened caches."""
    text = document.get("text", "")
    rows = []
    # Sheet boundaries must survive even when every newline was flattened.
    for section in re.split(r"\[sheet\s+", text)[1:]:
        sheet, _, body = section.partition("]")
        matches = list(re.finditer(r"\bR-\d+\s*\|", body))
        if not matches:
            continue
        headers = [fold(column.strip()) for column in body[:matches[0].start()].strip().split("|")]
        if not {"id", "risque", "probabilite", "impact", "statut"}.issubset(headers):
            continue
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
            raw = body[match.start():end].strip()
            columns = [column.strip() for column in raw.split("|")]
            fields = dict(zip(headers, columns))
            if not all(fields.get(key) for key in ("id", "risque", "statut")):
                continue
            rows.append({**fields, "document": document, "raw": raw,
                         "locator": f"Feuille {sheet.strip()} · {fields['id']}",
                         "register_date": register_date(document)})
    return rows


def _closed(status):
    return bool(re.fullmatch(r"ferme[e]?|clos[e]?|resolu[e]?|closed|resolved", fold(status).strip()))


def _explicit_resolution(row, documents):
    # A date inside the row is the status observation, not the workbook's date.
    observed = dates_in(row.get("commentaire", ""))
    baseline = max((item["date"] for item in observed), default=row["register_date"])
    if not baseline:
        return None
    generic = {"risque", "retard", "validation", "incomplete", "incomplet", "preparation", "projet"}
    terms = set(re.findall(r"\b[a-z]{4,}\b", fold(row["risque"]))) - generic
    candidates = []
    for document in documents:
        path = document.get("path", "")
        if path.startswith("08_Archives") or document.get("extension") not in {".eml", ".txt", ".md"}:
            continue
        text = document.get("text", "")
        # source_date handles normal email headers; flattened caches need the
        # original Date field isolated before the body.
        dated = document
        if document.get("extension") == ".eml":
            header = re.search(r"\bDate:\s*(.*?)(?=\s+(?:Bonjour|Salut|Merci)\b|$)", text)
            if header:
                dated = {**document, "text": f"Date: {header[1]}"}
        on = source_date(dated)
        if not on or on <= baseline:
            continue
        subject = re.search(r"\bSubject:\s*(.*?)(?=\s+From:|\n|$)", text)
        subject_value = fold(subject[1]) if subject else ""
        subject_matches = any(re.search(rf"\b{term}\b", subject_value) for term in terms)
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            value = fold(sentence)
            if not re.search(r"\brisque\b|\b" + re.escape(row["id"].lower()) + r"\b", value):
                continue
            if not (row["id"].lower() in value or subject_matches
                    or any(re.search(rf"\b{term}\b", value) for term in terms)):
                continue
            if re.search(r"\b(non|pas|jamais|si|pourrait|devrait|sera)\b|a confirmer|sous reserve", value):
                continue
            if re.search(r"\b(resolu|ferme|clos)\b", value):
                candidates.append({"document": document, "date": on, "excerpt": text,
                                   "locator": "Confirmation explicite de résolution"})
    return max(candidates, key=lambda item: item["date"]) if candidates else None


def current_risks(documents, limit=3):
    registers = [doc for doc in documents
                 if "registre" in fold(doc.get("path", "")) and "risque" in fold(doc.get("path", ""))
                 and doc.get("extension") == ".xlsx"
                 and not doc["path"].startswith("08_Archives")
                 and not doc["path"].split("/")[-1].startswith("~$")]
    if not registers:
        return None
    register = max(registers, key=lambda doc: (register_date(doc) or "", doc["path"]))
    rows = parse_rows(register)
    active, excluded = [], []
    for row in rows:
        if _closed(row["statut"]):
            excluded.append({**row, "exclusion": "closed"})
            continue
        resolution = _explicit_resolution(row, documents)
        if resolution:
            excluded.append({**row, "exclusion": "resolved", "resolution": resolution})
            continue
        # Unknown status is not silently promoted to an active risk.
        if fold(row["statut"]) in {"ouvert", "ouverte", "actif", "active", "en cours", "open", "en validation"}:
            active.append(row)
    weights = {"faible": 1, "moyen": 2, "moyenne": 2, "eleve": 3, "elevee": 3,
               "critique": 4, "low": 1, "medium": 2, "high": 3, "critical": 4}
    for row in active:
        probability, impact = weights.get(fold(row["probabilite"])), weights.get(fold(row["impact"]))
        row["priority_score"] = probability * impact if probability and impact else None
    active.sort(key=lambda row: (-(row["priority_score"] or 0), row["id"]))
    return {"register": register, "date": register_date(register), "rows": rows,
            "active": active if limit is None else active[:limit], "excluded": excluded,
            "active_count": len(active)}
