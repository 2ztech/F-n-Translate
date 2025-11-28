# component/translated_window_v2.py
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics
from PyQt5.QtWidgets import QWidget
import math

class TranslatedTextWindowV2(QWidget):
    """
    Stable overlay window: created once with fixed geometry (capture area).
    Accepts updates: list of line dicts => {'left','top','width','height','translated_text'}
    paintEvent draws all boxes. Does not resize itself.
    """
    def __init__(self, parent, capture_area):
        super().__init__(parent)
        self.capture_area = capture_area  # (x, y, w, h)
        x, y, w, h = capture_area
        # Window flags: always on top, transparent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_AlwaysStackOnTop)
        # Occupy the capture area and never change
        self.setGeometry(x, y, w, h)
        # lines to draw (in local coords relative to capture_area top-left)
        self._lines = []  # each: {'left','top','width','height','text'}
        self._font = QFont("Arial", 14)
        self._box_alpha = 200  # background alpha
        self._text_color = QColor(255, 255, 255)
        self._box_color = QColor(0, 0, 0, self._box_alpha)
        self._outline_color = QColor(0, 0, 0, 220)
        self.setMouseTracking(False)
        self.show()  # show once

    def update_lines(self, lines):
        """
        lines: list of dicts in absolute screen coords OR relative to capture area.
        We'll ensure they become relative by subtracting capture_area origin.
        Each item must contain 'translated_text' key.
        """
        x0, y0, _, _ = self.capture_area
        normalized = []
        for ln in lines:
            # assume ln has left, top, width, height, text
            left = ln['left'] - x0
            top = ln['top'] - y0
            normalized.append({
                'left': int(left),
                'top': int(top),
                'width': int(ln['width']),
                'height': int(ln['height']),
                'text': ln.get('translated_text', ln.get('text', ''))
            })
        self._lines = normalized
        # trigger paint once
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(self._font)
        fm = QFontMetrics(self._font)

        for ln in self._lines:
            left = ln['left']
            top = ln['top']
            width = ln['width']
            height = ln['height']
            text = ln['text']

            # Draw semi-transparent rounded rect background slightly larger than bbox
            pad_x = 6
            pad_y = 4
            rect = QRect(left - pad_x, top - pad_y, width + pad_x*2, height + pad_y*2)
            painter.setPen(Qt.NoPen)
            painter.setBrush(self._box_color)
            painter.drawRoundedRect(rect, 4, 4)

            # Draw outline to improve readability on busy backgrounds
            painter.setPen(self._outline_color)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 4, 4)

            # Draw text inside the rect - wrap if necessary
            # naive wrap: measure width and split by words
            max_w = rect.width() - 8
            # split into lines
            words = text.split()
            if not words:
                continue
            lines = []
            cur = words[0]
            for w in words[1:]:
                if fm.width(cur + " " + w) <= max_w:
                    cur = cur + " " + w
                else:
                    lines.append(cur)
                    cur = w
            lines.append(cur)
            # draw text lines
            painter.setPen(self._text_color)
            text_x = rect.left() + 6
            text_y = rect.top() + fm.ascent() + 4
            for line in lines:
                painter.drawText(text_x, text_y, line)
                text_y += fm.lineSpacing()

        painter.end()
