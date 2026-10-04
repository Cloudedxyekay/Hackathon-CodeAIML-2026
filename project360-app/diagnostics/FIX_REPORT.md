# Important bug fixes — October 4, 2026

All four substantive findings in the original diagnostic have been addressed.

| Finding | Result |
| --- | --- |
| Dossier shows historical target as current | Header, current facts, current owner, evidence date and action list now derive from project memory and synthesis. Original facts and action references are preserved separately in the historical section. |
| Explicit email commitments missing | Sentence-level extraction recognizes obligations within paragraphs and future first-person promises such as `Je mettrai`. Full-name matching tolerates accents and preserves canonical names. The three email commitments now appear with October 7, 12 and 13 deadlines in synthesis, dossier actions, update impact actions, JSON briefing and PDF. |
| Existing briefing disconnected from current state | `/api/brief` now uses the same current evidence-backed briefing model as the PDF. It no longer uses legacy baseline text for the target, owner, current gates or open actions. |
| PDF reuses old postponement reason and misses author | Each schedule-change decision uses its own source for authorship and quoted context. Nicolas is identified for the October 5 email. Missing motives remain explicitly unknown; the old connector explanation is not copied onto the new postponement. |

The dossier re-analysis also refreshes the parent dashboard so its cached state does not lag behind the regenerated dossier. Original budget information is clearly labelled as the documented initial budget, with subsequent changes available in Finance. The committee's initial launch prerequisites are described as historical requirements; current blockers are listed separately.

Validation:

- **73 backend regression tests pass**, including seven new cases covering paragraph commitments, canonical names, quoted/passive exclusions, current/historical separation, briefing/PDF agreement, attribution, missing versus explicit motives, and empty-source behavior.
- **Five frontend regressions pass.**
- **Production build passes.**
- **Seven browser/data checks pass** using the actual IDE test email in an isolated copy: import and specific actions; dossier current facts/history/deadlines/export; existing briefing; PDF content and authorship; removal/restoration/reload/re-analysis; absence of browser exceptions/model calls; original-data hashes.
- Importing the email changes the approved date from October 22 to October 29, while keeping all three launch gates open. Removing it returns the dossier and briefing to October 22; restoring it returns both to October 29.
- **114 original corpus/data files remain byte-for-byte unchanged.** The test email was not imported into the working project.
- Ask NOVA and live Ollama/enrichment calls remain excluded.

Implementation files: `server/synthesis.py`, `server/dossier.py`, `server/executive_pdf.py`, `server/main.py`, `server/updates.py`, and `src/components/Dossier.jsx`. Regression coverage: `server/test_current_state.py`. Browser evidence: `diagnostics/fix-results.json` and `diagnostics/verify_fixes.py`.

Existing date-only calendar exports are unchanged; exact hours remain in the preserved action text and source excerpts. Extraction remains rule-based and marks general commitments as documented, with fulfillment unconfirmed; it does not invent completion.

Restart the backend if it is not running with reload enabled, and refresh the browser to load the updated UI. No re-import or mutation of existing project sources is needed to obtain the corrected dossier and briefing for sources already active in project memory.
