"""
Aura-X Screen Monitor — Enhanced Real-Time
Continuous screen monitoring with rich context for AI-driven automation.
Provides active window tracking, OCR text, clickable element detection,
and screen change detection.
"""

import threading
import time
import io
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass, field
from core.logger import setup_logger

logger = setup_logger("aura_x.vision.capture")

try:
    import pyautogui
    import PIL.Image
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logger.warning("pyautogui not available. Screen capture disabled.")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


@dataclass
class ScreenFrame:
    """A captured screen frame with all extracted data."""
    image: Optional[object] = None
    timestamp: float = 0.0
    width: int = 0
    height: int = 0
    ocr_text: str = ""
    active_window: str = ""
    structured_regions: list = field(default_factory=list)
    clickable_elements: list = field(default_factory=list)
    layout: dict = field(default_factory=dict)
    changed: bool = False  # Whether screen content changed significantly


class ScreenMonitor:
    """
    Real-time screen monitor that continuously captures and analyzes the screen.
    Provides rich context for the AI agent to understand and interact with the desktop.
    """

    def __init__(self, interval: float = 0.5, enabled: bool = True):
        self.interval = interval
        self.enabled = enabled and PYAUTOGUI_AVAILABLE
        self.running = False
        self._current_frame: Optional[ScreenFrame] = None
        self._previous_text: str = ""
        self._frame_lock = threading.Lock()
        self._ocr_engine = None
        self._stop_event = threading.Event()
        self._frame_count = 0
        self._ocr_interval = 3  # Full OCR every N frames (saves CPU)
        self._quick_interval = 1  # Quick check every N frames
        self._watch_mode = False  # Enhanced monitoring mode
        self._callbacks = []  # GUI callbacks for screen changes

        if self.enabled:
            self._init_ocr()
            pyautogui.FAILSAFE = False

    def _init_ocr(self):
        try:
            from vision.ocr_engine import OCREngine
            self._ocr_engine = OCREngine()
            if self._ocr_engine.is_available():
                logger.info("OCR engine loaded — real-time screen reading active")
            else:
                logger.info("OCR engine loaded — basic mode (Tesseract not found)")
        except Exception as e:
            logger.warning(f"OCR engine not available: {e}")

    def start(self):
        """Start continuous screen monitoring."""
        if not self.enabled:
            logger.info("Screen monitor disabled")
            return
        self.running = True
        self._stop_event.clear()
        logger.info(f"Screen monitor started — interval: {self.interval}s, OCR every {self._ocr_interval} frames")
        self._capture_loop()

    def stop(self):
        """Stop monitoring."""
        self.running = False
        self._stop_event.set()

    def set_watch_mode(self, enabled: bool):
        """Enable/disable enhanced watch mode (more frequent OCR)."""
        self._watch_mode = enabled
        if enabled:
            self._ocr_interval = 1  # OCR every frame in watch mode
            logger.info("Screen watch mode ENABLED — continuous OCR active")
        else:
            self._ocr_interval = 3  # Normal interval
            logger.info("Screen watch mode disabled")

    def add_callback(self, callback):
        """Add a callback for screen changes (used by GUI)."""
        self._callbacks.append(callback)

    def _capture_loop(self):
        while self.running and not self._stop_event.is_set():
            start = time.time()
            try:
                self._capture_frame()
            except Exception as e:
                logger.debug(f"Capture error: {e}")
            elapsed = time.time() - start
            sleep_time = max(0, self.interval - elapsed)
            time.sleep(sleep_time)

    def _capture_frame(self):
        """Capture a screenshot and extract data."""
        try:
            screenshot = pyautogui.screenshot()
            w, h = screenshot.size
            frame = ScreenFrame(
                image=screenshot,
                timestamp=time.time(),
                width=w,
                height=h
            )

            # Always get active window (fast)
            frame.active_window = self._get_active_window()

            self._frame_count += 1

            # OCR processing at configured interval
            if self._ocr_engine and self._frame_count % self._ocr_interval == 0:
                try:
                    # Full text extraction
                    frame.ocr_text = self._ocr_engine.extract_text(screenshot)

                    # Detect if screen changed significantly
                    if self._previous_text:
                        frame.changed = self._text_changed(self._previous_text, frame.ocr_text)
                    self._previous_text = frame.ocr_text

                    # Extract structured regions (less frequently)
                    if self._frame_count % (self._ocr_interval * 2) == 0 or self._watch_mode:
                        frame.structured_regions = self._ocr_engine.extract_regions(screenshot)
                        frame.clickable_elements = self._ocr_engine.get_clickable_elements(screenshot)

                    # Layout analysis (even less frequently)
                    if self._frame_count % (self._ocr_interval * 4) == 0 or self._watch_mode:
                        frame.layout = self._ocr_engine.analyze_screen_layout(screenshot)

                except Exception as e:
                    logger.debug(f"OCR processing error: {e}")

            with self._frame_lock:
                self._current_frame = frame

            # Notify callbacks if screen changed
            if frame.changed and self._callbacks:
                for cb in self._callbacks:
                    try:
                        cb(frame)
                    except Exception:
                        pass

        except Exception as e:
            logger.debug(f"Screenshot error: {e}")

    def _text_changed(self, old_text: str, new_text: str) -> bool:
        """Detect if screen content changed significantly."""
        if not old_text or not new_text:
            return bool(new_text)
        # Simple similarity check
        old_words = set(old_text.lower().split())
        new_words = set(new_text.lower().split())
        if not old_words and not new_words:
            return False
        overlap = len(old_words & new_words)
        total = max(len(old_words | new_words), 1)
        similarity = overlap / total
        return similarity < 0.7  # More than 30% changed

    def _get_active_window(self) -> str:
        """Get the currently active window title."""
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value
        except Exception:
            return ""

    # ─── Public Query Methods ─────────────────────────────────

    def get_current_frame(self) -> Optional[ScreenFrame]:
        """Get the latest screen frame."""
        with self._frame_lock:
            return self._current_frame

    def get_context_summary(self) -> str:
        """
        Get a comprehensive, AI-friendly summary of the current screen.
        This is the primary method used by the agent for screen awareness.
        """
        frame = self.get_current_frame()
        if not frame:
            return ""

        lines = []

        # Active window
        if frame.active_window:
            lines.append(f"ACTIVE WINDOW: {frame.active_window}")

        # Screen dimensions
        lines.append(f"SCREEN: {frame.width}x{frame.height}")

        # OCR text (the most important data for the agent)
        if frame.ocr_text:
            # Truncate intelligently
            text = frame.ocr_text.strip()
            if len(text) > 2000:
                text = text[:2000] + "\n... [truncated]"
            lines.append(f"\nVISIBLE TEXT ON SCREEN:\n{text}")

        # Clickable elements
        if frame.clickable_elements:
            elements = []
            for elem in frame.clickable_elements[:20]:
                elements.append(f"  [{elem['text']}] at ({elem['center_x']}, {elem['center_y']})")
            lines.append(f"\nCLICKABLE ELEMENTS ({len(frame.clickable_elements)}):")
            lines.extend(elements)

        # Layout info
        if frame.layout and frame.layout.get("text_found"):
            layout = frame.layout.get("layout", {})
            parts = []
            if layout.get("has_toolbar"):
                parts.append("toolbar")
            if layout.get("has_sidebar"):
                parts.append("sidebar")
            if layout.get("has_statusbar"):
                parts.append("status bar")
            if parts:
                lines.append(f"\nLAYOUT: {', '.join(parts)} detected")
            lines.append(f"UI REGIONS: {frame.layout.get('content_regions', 0)} content areas")

        return "\n".join(lines)

    def find_text_on_screen(self, search_text: str) -> Optional[Tuple[int, int]]:
        """Find text on screen and return its position. Used for click automation."""
        frame = self.get_current_frame()
        if not frame or not frame.image or not self._ocr_engine:
            return None

        return self._ocr_engine.find_text_position(frame.image, search_text)

    def get_screen_text(self) -> str:
        """Get just the OCR text from the current frame."""
        frame = self.get_current_frame()
        return frame.ocr_text if frame else ""

    def get_clickable_elements(self) -> List[Dict]:
        """Get clickable elements from the current frame."""
        frame = self.get_current_frame()
        return frame.clickable_elements if frame else []

    def capture_region(self, x: int, y: int, width: int, height: int):
        """Capture a specific screen region."""
        try:
            return pyautogui.screenshot(region=(x, y, width, height))
        except Exception as e:
            logger.error(f"Region capture error: {e}")
            return None

    def find_on_screen(self, template_path: str, confidence: float = 0.8):
        """Find a template image on screen (for visual element matching)."""
        if not CV2_AVAILABLE:
            return None
        try:
            frame = self.get_current_frame()
            if not frame or not frame.image:
                return None
            screen_np = np.array(frame.image)
            screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_RGB2GRAY)
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                return None
            result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val >= confidence:
                h, w = template.shape
                cx = max_loc[0] + w // 2
                cy = max_loc[1] + h // 2
                return (cx, cy, max_val)
        except Exception as e:
            logger.debug(f"Template match error: {e}")
        return None

    def take_snapshot(self) -> Optional[ScreenFrame]:
        """Take an immediate snapshot with full OCR (ignores intervals)."""
        if not self.enabled:
            return None
        try:
            screenshot = pyautogui.screenshot()
            frame = ScreenFrame(
                image=screenshot,
                timestamp=time.time(),
                width=screenshot.size[0],
                height=screenshot.size[1]
            )
            frame.active_window = self._get_active_window()
            if self._ocr_engine:
                frame.ocr_text = self._ocr_engine.extract_text(screenshot)
                frame.structured_regions = self._ocr_engine.extract_regions(screenshot)
                frame.clickable_elements = self._ocr_engine.get_clickable_elements(screenshot)
                frame.layout = self._ocr_engine.analyze_screen_layout(screenshot)
            return frame
        except Exception as e:
            logger.error(f"Snapshot error: {e}")
            return None

    def get_status(self) -> Dict:
        return {
            "enabled": self.enabled,
            "running": self.running,
            "watch_mode": self._watch_mode,
            "frame_count": self._frame_count,
            "ocr_available": self._ocr_engine.is_available() if self._ocr_engine else False,
            "has_current_frame": self._current_frame is not None,
            "ocr_engine": self._ocr_engine.get_status() if self._ocr_engine else None
        }
