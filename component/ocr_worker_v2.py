# component/ocr_worker_v2.py
from PyQt5.QtCore import QThread, pyqtSignal
from PIL import Image
import pytesseract
from pytesseract import Output
import io
from typing import List, Dict, Tuple
import time

# Minimal preprocessing to keep OCR fast and reliable
def preprocess_image_for_ocr(pil_img: Image.Image) -> Image.Image:
    # convert to grayscale and optionally resize down/up depending on DPI
    img = pil_img.convert("L")
    # optional: resize a bit if tiny or huge; keep moderate resampling
    w, h = img.size
    max_dim = 1600
    if max(w, h) > max_dim:
        ratio = max_dim / max(w, h)
        img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
    return img

class OCRWorkerV2(QThread):
    # Emits a list of groups. Each group: {'text': str, 'left':int, 'top':int, 'width':int, 'height':int, 'conf':float}
    lines_extracted = pyqtSignal(list)  

    def __init__(self, screenshot_queue, lang_code='eng', parent=None):
        super().__init__(parent)
        self.screenshot_queue = screenshot_queue
        self.lang_code = lang_code
        self._running = True
        # Tesseract path if needed:
        # pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    def run(self):
        while self._running:
            try:
                screenshot = self.screenshot_queue.get()
                if screenshot is None:
                    continue
                # screenshot may be an mss shot object or PIL image; handle both
                if hasattr(screenshot, 'rgb') and hasattr(screenshot, 'size'):
                    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                elif isinstance(screenshot, Image.Image):
                    img = screenshot
                else:
                    # handle raw bytes
                    try:
                        img = Image.open(io.BytesIO(screenshot))
                    except Exception:
                        continue

                img = preprocess_image_for_ocr(img)

                # Get detailed data including word-level bboxes and line grouping info
                data = pytesseract.image_to_data(img, lang=self.lang_code, output_type=Output.DICT, config='--psm 6 --oem 1')
                grouped_lines = self._group_by_line(data)

                # Emit only if we found meaningful text
                if grouped_lines:
                    self.lines_extracted.emit(grouped_lines)

                # small sleep to allow throttle if upstream pushes too fast
                time.sleep(0.02)

            except Exception as e:
                # keep running on errors
                print("OCRWorkerV2 error:", e)
                time.sleep(0.1)

    def _group_by_line(self, data: Dict) -> List[Dict]:
        """
        Group word boxes into line-level boxes using block_num and line_num (tesseract fields).
        Return a list of groups with concatenated text plus bounding box.
        """
        grouped = {}
        n = len(data.get('text', []))
        for i in range(n):
            text = (data['text'][i] or "").strip()
            conf = float(data['conf'][i]) if data['conf'][i] != '-1' else -1.0
            if not text:
                continue
            block = int(data.get('block_num', [0])[i])
            line = int(data.get('line_num', [0])[i])
            key = (block, line)
            left = int(data['left'][i])
            top = int(data['top'][i])
            w = int(data['width'][i])
            h = int(data['height'][i])
            right = left + w
            bottom = top + h

            if key not in grouped:
                grouped[key] = {
                    "words": [text],
                    "left": left,
                    "top": top,
                    "right": right,
                    "bottom": bottom,
                    "conf_values": [conf]
                }
            else:
                grouped[key]["words"].append(text)
                grouped[key]["left"] = min(grouped[key]["left"], left)
                grouped[key]["top"] = min(grouped[key]["top"], top)
                grouped[key]["right"] = max(grouped[key]["right"], right)
                grouped[key]["bottom"] = max(grouped[key]["bottom"], bottom)
                grouped[key]["conf_values"].append(conf)

        # Format groups: compute aggregated confidence and joined text
        output = []
        for k, v in grouped.items():
            avg_conf = sum([c for c in v["conf_values"] if c >= 0]) / max(1, len([c for c in v["conf_values"] if c >= 0]))
            text = " ".join(v["words"])
            width = v["right"] - v["left"]
            height = v["bottom"] - v["top"]
            output.append({
                "text": text.strip(),
                "left": v["left"],
                "top": v["top"],
                "width": width,
                "height": height,
                "conf": avg_conf
            })

        # Sort by top (reading order)
        output.sort(key=lambda x: (x['top'], x['left']))
        return output

    def stop(self):
        self._running = False
        self.quit()
        self.wait()
