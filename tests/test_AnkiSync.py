import unittest

import AnkiSync as sync


class TestAnkiSyncHelpers(unittest.TestCase):
    def test_normalize_json_payload_strips_code_block(self) -> None:
        payload = "```json\n[{\"english\": \"hi\"}]\n```"
        self.assertEqual(sync.normalize_json_payload(payload), '[{"english": "hi"}]')

    def test_parse_word_pairs_returns_list(self) -> None:
        content = '[{"english": "hi", "foreign": "안녕"}]'
        result = sync.parse_word_pairs(content)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["english"], "hi")

    def test_build_note_structure(self) -> None:
        note = sync.build_note("Deck", "Front", "Back")
        self.assertEqual(note["deckName"], "Deck")
        self.assertEqual(note["fields"]["Front"], "Front")
        self.assertEqual(note["fields"]["Back"], "Back")


if __name__ == "__main__":
    unittest.main()
