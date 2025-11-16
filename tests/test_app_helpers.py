import unittest

import app


class TestAppHelpers(unittest.TestCase):
    def test_extract_image_filename_handles_single_quotes(self) -> None:
        html = "<div><img src='12345.png' /></div>"
        self.assertEqual(app.extract_image_filename(html), "12345.png")

    def test_extract_image_filename_handles_double_quotes(self) -> None:
        html = '<div><img src="nested/path/67890.png"></div>'
        self.assertEqual(app.extract_image_filename(html), "67890.png")


if __name__ == "__main__":
    unittest.main()
