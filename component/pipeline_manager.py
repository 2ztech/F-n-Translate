# component/pipeline_manager.py
import time
from queue import Queue
from component.ocr_worker_v2 import OCRWorkerV2
from component.translate_queue import TranslateQueue
from component.text_dedupe import DedupeEngine
from component.translated_window_v2 import TranslatedTextWindowV2
from core.translate_core import TranslationService  # your existing wrapper
from PyQt5.QtCore import QObject, pyqtSignal
from mss import mss
from PIL import Image

class PipelineManager(QObject):
    status_update = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None, capture_area=None, monitor_index=1):
        super().__init__(parent)
        self.parent = parent
        self.capture_area = capture_area  # (x,y,w,h) absolute screen coords
        self.monitor_index = monitor_index
        self.screenshot_queue = Queue(maxsize=4)

        # OCR worker
        self.ocr_worker = OCRWorkerV2(self.screenshot_queue, lang_code='eng')
        self.ocr_worker.lines_extracted.connect(self._handle_lines)
        self.ocr_worker.start()

        # translation engine & queue
        self.translation_service = TranslationService()  # must expose translate(text, source_lang, target_lang)
        self.tq = TranslateQueue(self._call_translate, max_workers=2)

        # dedupe
        self.dedupe = DedupeEngine(similarity_threshold=85, hold_seconds=2.5)

        # overlay window
        self.overlay = TranslatedTextWindowV2(parent=None, capture_area=self.capture_area)

        # throttle & last known lines
        self.last_displayed = []  # list of dicts as used by overlay
        self.capture_interval = 1.5  # seconds
        self._stop_flag = False

    def start(self):
        self._stop_flag = False
        self._capture_loop_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_loop_thread.start()
        self.status_update.emit("Pipeline started")

    def stop(self):
        self._stop_flag = True
        self.ocr_worker.stop()
        self.tq.shutdown()
        self.overlay.close()

    def _capture_loop(self):
        with mss() as sct:
            # calculate monitor capture rect if capture_area None (you may adapt)
            if not self.capture_area:
                monitor = sct.monitors[self.monitor_index]
                self.capture_area = (monitor['left'], monitor['top'], monitor['width'], monitor['height'])
            x, y, w, h = self.capture_area
            while not self._stop_flag:
                try:
                    monitor_region = {'left': x, 'top': y, 'width': w, 'height': h}
                    shot = sct.grab(monitor_region)
                    # put raw shot into queue; OCRWorkerV2 will convert to PIL
                    if not self.screenshot_queue.full():
                        self.screenshot_queue.put(shot)
                    time.sleep(self.capture_interval)
                except Exception as e:
                    self.error_occurred.emit(str(e))
                    time.sleep(1)

    def _handle_lines(self, lines):
        """
        lines: list of {'text','left','top','width','height','conf'}
        We will group text into a single block string per line (already done), perform dedupe check.
        If new, submit to translate queue; once translation returns, call overlay.update_lines()
        """

        # For visual stability, build candidate lines with same structure but include original text
        # Decide grouping granularity here: lines already, so for each line:
        for ln in lines:
            text = ln['text'].strip()
            if not text:
                continue

            if not self.dedupe.should_translate(text):
                # Skip if too similar / held
                continue

            # submit for translation; callback will receive translated text and metadata
            def _cb(translated, meta, orig=ln):
                if translated is None:
                    # keep last display if translation failed; optionally show error
                    print("Translation failed for:", orig['text'], meta)
                    return
                # attach translated text to bounding boxes and update overlay (one-line update)
                mapped = {
                    'left': orig['left'],
                    'top': orig['top'],
                    'width': orig['width'],
                    'height': orig['height'],
                    'translated_text': translated
                }
                # update overlay: we might want to merge existing lines with this one
                # For simplicity, update by replacing any line with same top value
                self._update_overlay_with_line(mapped)

            # submit
            self.tq.submit(text, 'auto', 'en', lambda tr, m: _cb(tr, m))

    def _update_overlay_with_line(self, mapped_line):
        # merge into last_displayed by top coordinate (or simple replace)
        replaced = False
        for i, ln in enumerate(self.last_displayed):
            # if vertical overlap, replace
            if abs(ln['top'] - mapped_line['top']) < 8:  # tolerance for top coordinate
                self.last_displayed[i] = mapped_line
                replaced = True
                break
        if not replaced:
            self.last_displayed.append(mapped_line)
        # limit to N lines to avoid memory issues
        self.last_displayed = sorted(self.last_displayed, key=lambda x: x['top'])[:40]
        # push to overlay window
        self.overlay.update_lines(self.last_displayed)
