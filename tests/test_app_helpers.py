import os
import unittest
from unittest.mock import patch

import app


class TestAppHelpers(unittest.TestCase):
    def test_extract_image_filename_handles_single_quotes(self) -> None:
        html = "<div><img src='12345.png' /></div>"
        self.assertEqual(app.extract_image_filename(html), "12345.png")

    def test_extract_image_filename_handles_double_quotes(self) -> None:
        html = '<div><img src="nested/path/67890.png"></div>'
        self.assertEqual(app.extract_image_filename(html), "67890.png")


class TestDeckImagesRoute(unittest.TestCase):
    def setUp(self) -> None:
        self.client = app.app.test_client()
        app.app.testing = True

    @patch("app.invoke")
    def test_deck_images_returns_entries_with_fallback_names(self, mock_invoke) -> None:
        hashed_filename = "12345-abcdef.png"
        base_name = "12345.png"
        image_path = app.IMAGE_DIR / base_name
        image_path.write_bytes(b"fake")

        mock_invoke.side_effect = [
            [42],
            [
                {
                    "fields": {
                        "Front": {"value": f'<img src="{hashed_filename}">'},
                        "Back": {"value": "Hello"},
                    }
                }
            ],
        ]

        response = self.client.get("/api/deck-images?deck=Test")
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["images"]), 1)
        self.assertTrue(data["images"][0]["image_url"].endswith(base_name))

        image_path.unlink()


if __name__ == "__main__":
    unittest.main()
