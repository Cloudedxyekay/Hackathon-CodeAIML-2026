# NOVA diagnostic report — October 4, 2026

**Follow-up:** the four substantive findings below have now been fixed and verified. See [FIX_REPORT.md](FIX_REPORT.md). This document preserves the original diagnostic findings.

The main workflows run successfully, but the application does **not yet meet every challenge requirement reliably**. Four substantive issues remain in current-state summaries, commitment extraction, and the explanation of newly imported decisions. They were deliberately left unchanged because fixing them would change core analysis behavior.

## Scope and precautions

- Tested Dashboard, Dossier, Evidence, Timeline, Calendrier, Avancement, Updates, project comparison, JSON/ICS exports, original downloads, and executive brief/PDF.
- Did not exercise Ask NOVA or call Ollama. The diagnostic browser blocked Ask and enrichment endpoints; the isolated backend rejected model operations. Some existing risk/recent-change regression tests use mocked model interfaces; these did not contact a model.
- Also excluded live **Enrichir IA**, because it uses the same local model dependency. Natural-language answers and optional AI enrichment are therefore not certified by this report.
- Ran mutation scenarios on copied corpus/data under `diagnostics/sandbox`, using separate backend/frontend ports 8010/5174. Your IDE's fictitious October 5 email was imported only there.
- Verified SHA-256 hashes of **114 original corpus/data files** before and after testing: no changes.
- Browser checks used installed Chrome in headless mode. Mobile checks used a simulated 390-pixel viewport, not a physical phone. No claim is made about Safari, Firefox, concurrent users, or long-term load.

## Validation results

| Area | Result and evidence |
| --- | --- |
| Production build | Pass: `npm.cmd run build`; 1,589 modules transformed. |
| Backend regressions | **66/66 pass** after correcting the Windows test-fixture encoding. Suites: intelligence, updates, dossier, synthesis, risk register, recent changes, comparison, executive PDF. |
| Frontend regressions | **5/5 pass**, covering document grouping, ordering, duplicate proofs, completion/archive semantics, and publication dates. |
| Dependency consistency | `pip check` passed. Installed requirements-dev HTTP client and Playwright in the local virtual environment for diagnostics. |
| Browser workflows | Initial 19 grouped happy-path scenarios passed. Follow-up checks reproduced failures, then verified the permitted minor fixes. Final six grouped browser/data checks pass. |
| Dashboard | Approved target, project-owner transition, ticket counts, open gates, documentary alerts, and navigation work. |
| Timeline | Search, accents, empty results, four filter controls, evidence drawer, extracted document, archive/restore, and local re-analysis work. |
| Calendar/progress | Month navigation, selected day, plan/ticket display and ICS download work. Updated launch date is in ICS; folded lines stay within the calendar format's 75-byte limit. |
| Dossier | Category navigation, filter controls, active/completed switch, JSON export, source reader and original download work. Current-state summary problem remains below. |
| Evidence | Searches for INV-003, SEC-210, sécurité, accessibilité and nonexistent text work. After the fix, HTTP 503/malformed responses show an error; retry, Enter, blank-query guard and no-results message work. |
| Updates | Preview and analysis do not mutate current project memory. Reviewed-text edits disable integration until re-analysis. Invalid dates, unsupported/empty files, invalid identifiers and malformed PDF have controlled outcomes. |
| Formats | EML, TXT, MD, CSV, XLSX and text PDF extracted successfully. PNG/JPG/JPEG/WEBP are accepted with warnings and a transcription fallback; automatic OCR is unavailable on this machine. |
| Import lifecycle | Approved-date changes propagate to dashboard, memory, timeline, dossier registers, synthesis and search. Repeated integration is idempotent. Remove/restore and re-ingestion preserve the intended state and original bytes. |
| Authority distinction | A supplier saying SEC-210 is closed does not close the reviewer's launch gate. A proposed date does not replace an approved date. |
| Launch gate lifecycle | Explicit reviewer confirmations close SEC-210, ACC-303 and OPS-601. With all three closed, gates drop to zero, completed tickets reach 8 and launch is no longer conditional. Dossier gate tasks and PDF blockers update. Removing the diagnostic confirmations restores the prior gates. |
| Comparison | ATLAS demo, custom project upload, all eight comparison axes, scoped proof downloads, JSON export, duplicate-selection validation and separate storage pass. NOVA state stays unchanged. |
| PDF | Downloads and parses successfully, has source references, reflects the latest approved target and removes closed gate actions. Its decision explanation is not fully dynamic; see issue 4. |
| Responsive layout | Dashboard, Dossier, Evidence, Timeline, Calendrier, Updates and Bonus have no document-level horizontal overflow at 390 pixels after the small grid fix. |

## Substantive findings — not changed

### 1. High: dossier presents a historical target as current

**Reproduction:** import `NOVA_TEST_Report_lancement_et_SEC210.eml`. Dashboard, memory and calendar correctly change the approved target from October 22 to **October 29, 2026**, keeping ACC-303, SEC-210 and OPS-601 open. Open the dossier's launch category.

**Observed:** its prominent “Informations pertinentes” still includes `La date actuellement approuvee est le 22 octobre 2026.` The same static facts are also shown under the historical section, while the derived registers contain the new information. Static `open_items` also keep old/unknown deadlines after the email introduces October 12 and 13 deadlines.

**Impact:** two views give conflicting answers to “What is currently valid?” Historical information is preserved correctly, but is also presented as current. A correction needs to separate historical reference facts from live state and compute current open actions from the same source as memory.

**Relevant implementation:** `server/dossier.py` copies `facts` and `open_items` from `data/processed/dossier.json`; `src/components/Dossier.jsx` renders these as prominent category facts/actions.

### 2. High: explicit email commitments are absent from the commitment register

The test email includes three concrete commitments:

| Person | Commitment | Deadline in source |
| --- | --- | --- |
| Nicolas Perron | Update launch plan and communications | October 7, 16:00 |
| Sophie Lambert | Re-test administrator logging and email report | October 12, 15:00 |
| Melissa Gagnon | Repeat modal keyboard tests and post report to Teams | October 13, 16:00 |

**Observed:** the timeline creates all three planned deadline events, but `/api/synthesis` has **zero commitment entries linked to this imported document**. Consequently, the dossier's engagement register does not capture them either. The update action list contains general schedule/gate follow-ups rather than these three explicit tasks.

**Cause:** `server/synthesis.py` extracts actions line by line. Nicolas's future promise and Sophie's obligation occur after another sentence on the same line; the first-person matcher also does not handle `Je mettrai`. The Melissa line is affected by how accented/unaccented names are recognized against the roster. Fixing this requires changes to extraction and reconciliation, so it was left untouched.

**Impact:** requirements about commitments, responsibilities and next actions are only partially satisfied for natural email prose. A calendar event should not be mistaken for a correctly attributed action in the engagement register. Time-of-day remains source text; generated deadline events and ICS are date-only.

### 3. Medium: existing executive briefing is disconnected from current state

**Reproduction:** open Bonus → existing briefing after an approved-date import.

**Observed:** `/api/brief` reports `A confirmer` for budget and launch date, even though project memory has a known approved launch target. It reads `baseline.json`, `actions.json` and `answers.json`; imports rebuild documents, chunks, project memory and timeline, not those legacy summaries.

**Impact:** the existing briefing cannot serve as a reliable handover summary. The downloadable PDF has a separate implementation and does update the target; the two briefing features are inconsistent. They should eventually share the current evidence model.

### 4. High: PDF invents the rationale for a newly imported postponement

**Reproduction:** generate the PDF after importing the October 5 email.

**Observed:** the new decision correctly says the launch moves to `2026-10-29`, but adds `Le report donne du temps pour stabiliser le connecteur et reprendre les tests.` That reason is hardcoded for every schedule change, even though the new email discusses security/keyboard validation and does not establish connector stabilization as the reason. The decision also says `Autorité non nommée dans cet extrait`, despite Nicolas identifying himself as project lead and confirming the decision.

**Impact:** a report can cite the right source and still give an unsupported explanation or miss the decision-maker. This affects “why was this decision made?” and source-grounded handover requirements.

**Relevant implementation:** the schedule-change loop in `server/executive_pdf.py`. The original connector-related reason is appropriate to its historical decision, but cannot be copied automatically onto every new decision.

## Minor fixes made and verified

1. **EvidenceSearch.jsx:** handle failed/malformed responses without crashing; loading/disabled state, Enter submission, input label and no-results feedback. Reproduced the original `Cannot read properties of undefined (reading 'map')` failure before fixing it.
2. **Dossier.jsx:** connect the already implemented source reader to an evidence button. Previously `onOpenSource` was passed to `Evidence` but ignored, leaving the modal unreachable. Verified modal text, Escape dismissal and original download.
3. **updates.css:** constrain the Updates grid track with `minmax(0, 1fr)`. Its file picker previously caused a 431-pixel document width on a 390-pixel viewport; final width is 390.
4. **updates.py:** replace the stray `?` between a ticket ID and title with `·`; this is display-only.
5. **test_risk_register.py:** read the UTF-8 fixture explicitly. Windows' default encoding previously corrupted accented headers in the test, causing four false failures; the production parser was correct.
6. **README.md:** remove unresolved merge-conflict marker lines, keeping the documented enrichment configuration.

No extraction rules, approval rules, core data structures, project sources or historical records were changed.

## Challenge coverage

| Requirement | Diagnostic assessment |
| --- | --- |
| Organize information | Works for the tested corpus and supported readable formats. OCR needs an additional local tool or reviewed transcription. |
| Associate documents/events with subjects | Categories, source links and direct ticket impact links work in tested scenarios. |
| Identify decisions, owners, commitments, deadlines and risks | Decisions, owner transitions, tickets and date extraction pass regressions. **Incomplete commitment extraction and PDF attribution remain.** |
| Reconstruct evolution over time | Timeline, target history, owner transitions, archive and source preservation work. |
| Distinguish historical/current information | Core memory does; **static dossier/briefing summaries do not consistently do so.** |
| Contradictions/missing/problematic information | Existing stale-plan/status/risk and open-gate alerts work. Detection is rule-based; arbitrary unseen contradictions are not certified. |
| Natural-language interrogation | **Excluded at your request.** |
| Justify outputs with sources | Originals/proof IDs resolve, downloads match bytes. **PDF rationale can still be unsupported.** |
| Propose next actions | General schedule and gate actions work; **the imported email's specific commitments are missed.** |
| Explain a new event and its impacts | Target/gate changes, linked previous events, source preservation and lifecycle work. Action extraction and decision rationale need the substantive corrections above. |

Recommended priority: fix current-versus-historical summary consistency, then explicit commitment extraction, then source-derived PDF reasoning/attribution and the legacy briefing. Until then, the dashboard/timeline are more reliable for the current launch target than the static dossier summary or existing briefing.

Raw diagnostic evidence and screenshots are stored beside this report. Earlier script outputs include intentionally reproduced failures and a few corrected diagnostic selector/fixture errors; the final verified conclusions above supersede those intermediate results.
