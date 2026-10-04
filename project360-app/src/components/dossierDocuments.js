export function documentSupport(path) {
  if (/Teams_/i.test(path)) return 'Microsoft Teams';
  if (/\.eml$/i.test(path)) return 'Courriel (application non précisée)';
  if (/\.xlsx$/i.test(path)) return 'Classeur Excel';
  if (/\.pdf$/i.test(path)) return 'Document PDF';
  if (/Transcript/i.test(path)) return 'Transcription de réunion';
  return 'Document texte';
}

export function groupDossierDocuments(sections) {
  const documents = new Map();
  for (const section of sections) {
    for (const [group, items] of Object.entries(section.registers || {})) {
      for (const item of items) {
        for (const proof of item.evidence || []) {
          const support = documentSupport(proof.path);
          const key = JSON.stringify([proof.document_id || proof.path, proof.published_on || null, support]);
          if (!documents.has(key)) documents.set(key, { key, path: proof.path, date: proof.published_on || null, support, categories: new Map(), groups: new Set(), statuses: new Set(), points: new Map(), evidence: new Map() });
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
  return [...documents.values()].map(entry => ({ ...entry, categories: [...entry.categories.values()], groups: [...entry.groups], statuses: [...entry.statuses], points: [...entry.points.values()], evidence: [...entry.evidence.values()] }));
}
