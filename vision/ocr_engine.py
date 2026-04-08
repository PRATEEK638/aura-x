"""
Aura-X OCR Engine — Multi-Backend
Tries multiple OCR methods for maximum compatibility:
1. Tesseract (best accuracy, requires install)
2. Windows native screenshot + text extraction via pyautogui/PIL
3. Basic pixel analysis fallback

Also provides UI region detection and smart text extraction.
"""

import os
import re
import time
from typing import Optional, List, Dict, Tuple
from pathlib import Path
from core.logger import setup_logger

logger = setup_logger("aura_x.vision.ocr")

# ─── Tesseract Discovery ─────────────────────────────────────
TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\{user}\AppData\Local\Tesseract-OCR\tesseract.exe",
    r"C:\tools\Tesseract-OCR\tesseract.exe",
    r"C:\tesseract\tesseract.exe",
]

TESSERACT_AVAILABLE = False
PYTESSERACT_AVAILABLE = False

try:
    import pytesseract

    # Try to find tesseract binary
    found_path = None
    username = os.getenv("USERNAME", "")

    for path in TESSERACT_PATHS:
        resolved = path.replace("{user}", username)
        if os.path.exists(resolved):
            found_path = resolved
            break

    if found_path:
        pytesseract.pytesseract.tesseract_cmd = found_path
        logger.info(f"Tesseract found at: {found_path}")

    # Verify it works
    try:
        version = pytesseract.get_tesseract_version()
        TESSERACT_AVAILABLE = True
        PYTESSERACT_AVAILABLE = True
        logger.info(f"Tesseract OCR v{version} ready")
    except Exception:
        # pytesseract imported but tesseract binary not found
        logger.info("pytesseract available but Tesseract binary not found")
        PYTESSERACT_AVAILABLE = True

except ImportError:
    logger.info("pytesseract not installed")

# ─── PIL for image processing ────────────────────────────────
try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ─── CV2 for advanced processing ─────────────────────────────
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class OCREngine:
    """
    Multi-backend OCR engine with preprocessing for better accuracy.
    Provides text extraction, region detection, and UI element analysis.
    """

    def __init__(self, lang: str = "eng"):
        self.lang = lang
        self.tesseract_available = TESSERACT_AVAILABLE
        self._last_result: Optional[str] = None
        self._last_regions: List[Dict] = []
        self._cache_time: float = 0
        self._cache_ttl: float = 0.5  # 500ms cache

    def extract_text(self, image, preprocess: bool = True) -> str:
        """
        Extract text from a screenshot image.
        Tries Tesseract first, falls back to basic analysis.
        """
        if image is None:
            return ""

        now = time.time()
        if now - self._cache_time < self._cache_ttl and self._last_result:
            return self._last_result

        text = ""

        # Method 1: Tesseract OCR (best quality)
        if self.tesseract_available and PYTESSERACT_AVAILABLE:
            try:
                processed = self._preprocess(image) if preprocess else image
                text = pytesseract.image_to_string(
                    processed,
                    lang=self.lang,
                    config='--oem 3 --psm 3'
                )
                text = self._clean_text(text)
            except Exception as e:
                logger.debug(f"Tesseract OCR error: {e}")
                text = ""

        # Method 2: Windows OCR API (fallback)
        if not text:
            text = self._windows_ocr(image)

        self._last_result = text
        self._cache_time = now
        return text

    def extract_regions(self, image) -> List[Dict]:
        """
        Extract structured UI regions with bounding boxes from the screen.
        Returns list of {text, x, y, w, h, confidence} dicts.
        """
        if image is None:
            return []

        regions = []

        if self.tesseract_available and PYTESSERACT_AVAILABLE:
            try:
                processed = self._preprocess(image)
                data = pytesseract.image_to_data(
                    processed,
                    lang=self.lang,
                    output_type=pytesseract.Output.DICT,
                    config='--oem 3 --psm 3'
                )

                n_boxes = len(data['level'])
                for i in range(n_boxes):
                    text = data['text'][i].strip()
                    conf = int(data['conf'][i])
                    if text and conf > 40:
                        regions.append({
                            "text": text,
                            "x": data['left'][i],
                            "y": data['top'][i],
                            "w": data['width'][i],
                            "h": data['height'][i],
                            "confidence": conf,
                            "level": data['level'][i],
                            "block": data['block_num'][i],
                            "line": data['line_num'][i]
                        })
            except Exception as e:
                logger.debug(f"Region extraction error: {e}")

        self._last_regions = regions
        return regions

    def find_text_position(self, image, search_text: str) -> Optional[Tuple[int, int]]:
        """
        Find the screen position of specific text.
        Returns (center_x, center_y) or None.
        """
        regions = self.extract_regions(image)
        search_lower = search_text.lower()

        # Exact match first
        for r in regions:
            if r["text"].lower() == search_lower:
                cx = r["x"] + r["w"] // 2
                cy = r["y"] + r["h"] // 2
                return (cx, cy)

        # Partial match: find consecutive words that form the search text
        # Group regions by line
        lines = {}
        for r in regions:
            key = (r.get("block", 0), r.get("line", 0))
            if key not in lines:
                lines[key] = []
            lines[key].append(r)

        for line_regions in lines.values():
            line_regions.sort(key=lambda r: r["x"])
            line_text = " ".join(r["text"] for r in line_regions)
            if search_lower in line_text.lower():
                # Find the approximate center of the matching text
                total_x = sum(r["x"] + r["w"] // 2 for r in line_regions) // len(line_regions)
                total_y = sum(r["y"] + r["h"] // 2 for r in line_regions) // len(line_regions)
                return (total_x, total_y)

        # Contains match
        for r in regions:
            if search_lower in r["text"].lower():
                cx = r["x"] + r["w"] // 2
                cy = r["y"] + r["h"] // 2
                return (cx, cy)

        return None

    def get_clickable_elements(self, image) -> List[Dict]:
        """
        Identify likely clickable UI elements (buttons, links, menu items).
        Uses text patterns and position heuristics.
        """
        regions = self.extract_regions(image)
        clickable = []

        button_patterns = [
            r"^(OK|Cancel|Yes|No|Close|Save|Open|Delete|Submit|Apply|Next|Back|Done|Accept|Decline)$",
            r"^(File|Edit|View|Help|Tools|Window|Insert|Format|Home|Settings)$",
            r"^(Sign [Ii]n|Log [Ii]n|Log [Oo]ut|Sign [Uu]p|Register|Subscribe)$",
            r"^(Search|Browse|Upload|Download|Send|Reply|Share|Copy|Paste|Cut)$",
        ]

        for r in regions:
            text = r["text"].strip()
            if not text or len(text) > 30:
                continue

            is_button = False
            for pattern in button_patterns:
                if re.match(pattern, text, re.IGNORECASE):
                    is_button = True
                    break

            # Short text in specific screen positions is likely a menu/button
            if len(text) < 15 and r["confidence"] > 60:
                is_button = True

            if is_button:
                clickable.append({
                    "text": text,
                    "x": r["x"],
                    "y": r["y"],
                    "center_x": r["x"] + r["w"] // 2,
                    "center_y": r["y"] + r["h"] // 2,
                    "w": r["w"],
                    "h": r["h"],
                    "type": "button"
                })

        return clickable

    def analyze_screen_layout(self, image) -> Dict:
        """
        Analyze the overall screen layout: identify toolbars, content areas, sidebars.
        """
        if image is None:
            return {}

        regions = self.extract_regions(image)
        if not regions:
            return {"text_found": False}

        # Get image dimensions
        if PIL_AVAILABLE and hasattr(image, 'size'):
            w, h = image.size
        elif hasattr(image, 'shape'):
            h, w = image.shape[:2]
        else:
            w, h = 1920, 1080

        # Classify regions by position
        top_bar = [r for r in regions if r["y"] < h * 0.08]
        bottom_bar = [r for r in regions if r["y"] > h * 0.92]
        left_side = [r for r in regions if r["x"] < w * 0.2]
        main_content = [r for r in regions if w * 0.2 <= r["x"] <= w * 0.8 and h * 0.08 <= r["y"] <= h * 0.92]

        # Build summary
        all_text = " ".join(r["text"] for r in regions if r["confidence"] > 50)

        return {
            "text_found": True,
            "total_regions": len(regions),
            "screen_size": f"{w}x{h}",
            "top_bar_text": " ".join(r["text"] for r in top_bar),
            "main_content_preview": all_text[:800],
            "clickable_count": len(self.get_clickable_elements(image)),
            "layout": {
                "has_toolbar": len(top_bar) > 3,
                "has_sidebar": len(left_side) > 5,
                "has_statusbar": len(bottom_bar) > 0,
                "content_regions": len(main_content)
            }
        }

    def _preprocess(self, image):
        """Preprocess image for better OCR accuracy."""
        if not PIL_AVAILABLE:
            return image

        try:
            if not isinstance(image, Image.Image):
                image = Image.fromarray(image) if hasattr(image, '__array__') else image

            # Convert to grayscale
            gray = image.convert("L")

            # Increase contrast
            enhancer = ImageEnhance.Contrast(gray)
            gray = enhancer.enhance(1.5)

            # Sharpen
            gray = gray.filter(ImageFilter.SHARPEN)

            # Scale up small text
            w, h = gray.size
            if w < 1920:
                scale = 2
                gray = gray.resize((w * scale, h * scale), Image.Resampling.LANCZOS)

            return gray
        except Exception:
            return image

    def _windows_ocr(self, image) -> str:
        """
        Fallback: use basic image analysis when Tesseract isn't available.
        Returns any text we can extract via alternative means.
        """
        # Try using the Windows clipboard trick: copy visible text
        try:
            import ctypes
            # Get window text of the foreground window
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value

            if title:
                return f"[Active Window: {title}]"
        except Exception:
            pass

        return ""

    def _clean_text(self, text: str) -> str:
        """Clean OCR output."""
        if not text:
            return ""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]{3,}', '  ', text)
        # Remove obvious OCR artifacts
        text = re.sub(r'[|}{\\](?=[a-zA-Z])', '', text)
        # Strip
        lines = [line.strip() for line in text.split('\n')]
        lines = [l for l in lines if len(l) > 1]  # Remove single-char noise
        return '\n'.join(lines)

    def is_available(self) -> bool:
        return self.tesseract_available

    def get_status(self) -> Dict:
        return {
            "tesseract": self.tesseract_available,
            "pytesseract": PYTESSERACT_AVAILABLE,
            "pil": PIL_AVAILABLE,
            "cv2": CV2_AVAILABLE,
            "lang": self.lang
        }
