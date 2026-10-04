import unittest

from .intelligence import build_project_memory
from .synthesis import build_synthesis


def synth(text):
    doc = {'id': 'doc-test', 'path': '02_Reunions/test.txt', 'extension': '.txt', 'text': text}
    return build_synthesis([doc], build_project_memory([doc]))


class SynthesisTests(unittest.TestCase):
    def test_explicit_actions_preserve_evidence_and_unknown_deadline(self):
        result = synth('Date : 7 juillet 2026\nActions\n- Marc : confirmer le connecteur.\nNote\nMarc participe au comité.')
        actions = result['groups']['engagements']
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['owner'], 'Marc')
        self.assertIsNone(actions[0]['due'])
        self.assertEqual(actions[0]['evidence'][0]['excerpt'], '- Marc : confirmer le connecteur.')

    def test_casual_speech_and_passive_obligations_are_not_assignments(self):
        result = synth("Date : 26 septembre 2026\n10:00 Nicolas : Je vais être bref.\nUne validation technique doit confirmer la migration.\nSophie rappelle que la journalisation devra être vérifiée.")
        self.assertEqual(result['groups']['engagements'], [])

    def test_first_person_promise_has_future_due_and_speaker_role(self):
        result = synth('Date : 26 septembre 2026\n10:12 Julien : Je vais livrer le correctif le 2 octobre 2026.')
        action = result['groups']['engagements'][0]
        self.assertEqual(action['owner'], 'Julien')
        self.assertEqual(action['owner_role'], 'Auteur de l’engagement')
        self.assertEqual(action['due'], '2026-10-02')

    def test_collective_obligation_keeps_owner_unknown(self):
        result = synth('Date : 10 septembre 2026\n15:25 Élodie : On doit mettre les plans à jour.')
        action = result['groups']['engagements'][0]
        self.assertIsNone(action['owner'])
        self.assertIn('On doit', action['title'])


if __name__ == '__main__':
    unittest.main()
