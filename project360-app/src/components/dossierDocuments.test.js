import test from 'node:test';
import assert from 'node:assert/strict';
import { groupDossierDocuments } from './dossierDocuments.js';

const proof = { document_id: 'doc-1', path: 'meeting.txt', published_on: '2026-09-10', locator: 'Ligne 1', excerpt: 'Décision' };
const item = { id: 'one', status: 'approved', evidence: [proof] };
test('one document includes multiple types and categories without duplicate points or proofs', () => {
  const entries = groupDossierDocuments([
    { id: 'pilotage', title: 'Pilotage', registers: { decisions: [item], engagements: [{ ...item, id: 'two' }] } },
    { id: 'production', title: 'Production', registers: { decisions: [item] } },
  ]);
  assert.equal(entries.length, 1);
  assert.equal(entries[0].points.length, 2);
  assert.equal(entries[0].categories.length, 2);
  assert.deepEqual(entries[0].groups, ['decisions', 'engagements']);
  assert.equal(entries[0].evidence.length, 1);
});
test('different documents on the same date stay separate', () => {
  const entries = groupDossierDocuments([{ id: 'a', registers: { decisions: [item, { ...item, id: 'two', evidence: [{ ...proof, document_id: 'doc-2', path: 'other.txt' }] }] } }]);
  assert.equal(entries.length, 2);
});
test('same document with different publication dates stays separate; due dates do not split it', () => {
  const make = (id, date, due) => ({ ...item, id, due, evidence: [{ ...proof, published_on: date }] });
  const entries = groupDossierDocuments([{ id: 'a', registers: { echeances: [make('1', '2026-09-10', '2026-10-15'), make('2', '2026-09-10', '2026-10-22'), make('3', '2026-09-11', null)] } }]);
  assert.equal(entries.length, 2);
  assert.equal(entries[0].points.length, 2);
});
