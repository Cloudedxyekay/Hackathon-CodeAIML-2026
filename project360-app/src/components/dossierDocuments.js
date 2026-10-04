export function documentSupport(path) {
  if (/\.(png|jpe?g|webp)$/i.test(path)) return 'Image / capture';
  if (/Teams_/i.test(path)) return 'Microsoft Teams';
  if (/\.eml$/i.test(path)) return 'Courriel (application non précisée)';
  if (/\.xlsx$/i.test(path)) return 'Classeur Excel';
  if (/\.pdf$/i.test(path)) return 'Document PDF';
  if (/Transcript/i.test(path)) return 'Transcription de réunion';
  return 'Document texte';
}

function newestFirst(first, second) {
  return (second || '').localeCompare(first || '');
}

export function groupDossierDocuments(sections, completedDocuments = []) {
  const completedIds = new Map(completedDocuments.map(document => [document.document_id, document]));
  const documents = new Map();
  for (const section of sections) {
    for (const [group, items] of Object.entries(section.registers || {})) {
      for (const item of items) {
        for (const proof of item.evidence || []) {
          if (["README.txt", "MANIFEST.csv"].includes(proof.path)) continue;
          const support = documentSupport(proof.path);
          const key = JSON.stringify([proof.document_id || proof.path, proof.published_on || null, support]);
          if (!documents.has(key)) documents.set(key, { key, path: proof.path, date: proof.published_on || null, support, completion: completedIds.get(proof.document_id) || null, categories: new Map(), groups: new Set(), statuses: new Set(), points: new Map(), evidence: new Map() });
          const entry = documents.get(key);
          entry.categories.set(section.id, { id: section.id, title: section.title });
          entry.groups.add(group);
          entry.statuses.add(item.status);
          entry.points.set(`${group}-${item.id}`, { group, item: { ...item, evidence: [proof] } });
          entry.evidence.set(JSON.stringify([proof.locator, proof.excerpt]), proof);
        }
      }
    }
  }
  return [...documents.values()].map(entry => ({
    ...entry,
    categories: [...entry.categories.values()],
    groups: [...entry.groups],
    statuses: [...entry.statuses],
    points: [...entry.points.values()].sort((a, b) => newestFirst(a.item.date, b.item.date)),
    evidence: [...entry.evidence.values()].sort((a, b) => newestFirst(a.published_on, b.published_on)),
  })).sort((a, b) => newestFirst(a.date, b.date));
}
