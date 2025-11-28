import unittest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.live_translation_service import TranslationWorker

class MockLogger:
    def info(self, msg): print(f"INFO: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")
    def debug(self, msg): print(f"DEBUG: {msg}")

class TestOCRGrouping(unittest.TestCase):
    def setUp(self):
        self.worker = TranslationWorker(None, "eng", "msa", MockLogger(), None)

    def test_group_lines_simple(self):
        # Mock pytesseract data
        data = {
            'text': ['Hello', 'World'],
            'conf': [90, 90],
            'left': [10, 60],
            'top': [10, 10],
            'width': [40, 40],
            'height': [20, 20]
        }
        
        lines = self.worker.group_lines(data)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['text'], "Hello World")

    def test_group_lines_multiline(self):
        # Mock pytesseract data for two lines that should be merged
        # Line 1: "This is a"
        # Line 2: "long sentence." (directly below)
        data = {
            'text': ['This', 'is', 'a', 'long', 'sentence.'],
            'conf': [90, 90, 90, 90, 90],
            'left': [10, 60, 110, 10, 60],
            'top': [10, 10, 10, 35, 35], # 2nd line is at y=35 (height is 20, so gap is 5)
            'width': [40, 40, 40, 40, 80],
            'height': [20, 20, 20, 20, 20]
        }
        
        lines = self.worker.group_lines(data)
        # Should be merged into one block
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['text'], "This is a long sentence.")

    def test_group_lines_separate_paragraphs(self):
        # Mock pytesseract data for two separate paragraphs
        # Para 1 at top
        # Para 2 way below
        data = {
            'text': ['Para', 'One', 'Para', 'Two'],
            'conf': [90, 90, 90, 90],
            'left': [10, 60, 10, 60],
            'top': [10, 10, 100, 100], # Big gap
            'width': [40, 40, 40, 40],
            'height': [20, 20, 20, 20]
        }
        
        lines = self.worker.group_lines(data)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]['text'], "Para One")
        self.assertEqual(lines[1]['text'], "Para Two")

if __name__ == '__main__':
    unittest.main()
