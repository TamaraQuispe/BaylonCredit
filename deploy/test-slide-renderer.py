"""Exercise editable/offline export and fail-closed geometry guards."""

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

from pptx import Presentation

SPEC = importlib.util.spec_from_file_location(
    "slide_renderer", Path(__file__).with_name("slide-renderer.py")
)
RENDERER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDERER)


class SlideRendererTests(unittest.TestCase):
    def setUp(self):
        self.slide = {
            "number": 1,
            "notes": "Speaker notes, not a human rehearsal",
            "elements": [
                {
                    "kind": "text",
                    "x": 0.5,
                    "y": 0.5,
                    "w": 8,
                    "h": 1,
                    "text": "A < B & C",
                },
                {
                    "kind": "table",
                    "x": 0.5,
                    "y": 2,
                    "w": 8,
                    "h": 1.5,
                    "headers": ["Model", "F2"],
                    "rows": [["SVM", "0.70115"]],
                    "widths": [5, 3],
                    "row_height": 0.75,
                },
            ],
        }

    def test_editable_text_table_notes_and_escaped_html(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            RENDERER.export_slides([self.slide], root, name="deck")
            pptx = Presentation(root / "deck.pptx")
            self.assertEqual(len(pptx.slides), 1)
            slide = pptx.slides[0]
            self.assertEqual(slide.shapes[0].text, "A < B & C")
            self.assertEqual(slide.shapes[1].table.cell(1, 0).text, "SVM")
            self.assertEqual(slide.notes_slide.notes_text_frame.text, self.slide["notes"])
            markup = (root / "deck.html").read_text()
            self.assertIn("A &lt; B &amp; C", markup)
            self.assertNotIn("<script", markup)

    def assert_rejected(self, slide, message):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, message):
                RENDERER.export_slides([slide], root)
            self.assertEqual(list(root.iterdir()), [])

    def test_out_of_bounds_and_nonfinite_elements(self):
        for key, value in [("x", -1), ("w", 14), ("h", 0), ("y", float("nan"))]:
            with self.subTest(key=key, value=value):
                slide = copy.deepcopy(self.slide)
                slide["elements"][0][key] = value
                self.assert_rejected(slide, "out-of-bounds")

    def test_inconsistent_table_dimensions(self):
        for key, value in [
            ("widths", [1, 1]),
            ("row_height", 1),
            ("headers", ["Only one"]),
            ("rows", [["Three", "columns", "bad"]]),
        ]:
            with self.subTest(key=key):
                slide = copy.deepcopy(self.slide)
                slide["elements"][1][key] = value
                self.assert_rejected(slide, "inconsistent table")

    def test_unknown_element_is_not_silently_dropped(self):
        self.slide["elements"][0]["kind"] = "unknown"
        self.assert_rejected(self.slide, "Unsupported element")


if __name__ == "__main__":
    unittest.main()
