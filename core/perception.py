"""
Aura-X Perception System
Context fusion combining UI automation + vision + system state.
"""

import platform
import time
from typing import Dict, Optional, List
from core.logger import setup_logger

logger = setup_logger("aura_x.core.perception")

PLATFORM = platform.system()


class PerceptionSystem:
    """
    Fuses data from multiple sources into a unified environment understanding:
    1. UI Automation (pywinauto) — primary, structured data
    2. Vision (OCR + screen capture) — fallback, pixel-based
    3. System state (processes, windows)
    """

    def __init__(self, screen_monitor=None):
        self.screen_monitor = screen_monitor
        self._ui_automation = None
        self._last_state: Dict = {}
        self._last_update: float = 0
        self._cache_ttl: float = 1.0  # seconds

        self._init_ui_automation()

    def _init_ui_automation(self):
        """Initialize pywinauto-based UI automation."""
        try:
            from automation.ui_automation import UIAutomation
            self._ui_automation = UIAutomation()
            logger.info("UI Automation (pywinauto) initialized")
        except ImportError:
            logger.info("pywinauto not available — using vision-only perception")
        except Exception as e:
            logger.warning(f"UI automation init error: {e}")

    def get_environment_state(self) -> Dict:
        """Get a fused view of the current environment."""
        now = time.time()
        if now - self._last_update < self._cache_ttl and self._last_state:
            return self._last_state

        state = {
            "timestamp": now,
            "platform": PLATFORM,
            "active_window": "",
            "window_list": [],
            "screen_text": "",
            "ui_elements": [],
            "processes": []
        }

        # Layer 1: UI Automation (primary)
        if self._ui_automation:
            try:
                ui_state = self._ui_automation.get_state()
                state["active_window"] = ui_state.get("active_window", "")
                state["window_list"] = ui_state.get("windows", [])
                state["ui_elements"] = ui_state.get("elements", [])
            except Exception as e:
                logger.debug(f"UI automation state error: {e}")

        # Layer 2: Vision (fallback/supplement)
        if self.screen_monitor:
            try:
                ctx = self.screen_monitor.get_context_summary()
                if ctx:
                    state["screen_text"] = ctx
                # Fill active window from vision if UI automation didn't get it
                if not state["active_window"]:
                    frame = self.screen_monitor.get_current_frame()
                    if frame and frame.active_window:
                        state["active_window"] = frame.active_window
            except Exception as e:
                logger.debug(f"Vision state error: {e}")

        # Layer 3: System state
        try:
            state["processes"] = self._get_running_processes()
        except Exception:
            pass

        self._last_state = state
        self._last_update = now
        return state

    def get_active_window_info(self) -> Dict:
        """Get detailed info about the currently active window."""
        if self._ui_automation:
            try:
                return self._ui_automation.get_active_window_detail()
            except Exception:
                pass

        # Fallback to ctypes
        info = {"title": "", "process": ""}
        try:
            if PLATFORM == "Windows":
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                info["title"] = buf.value
        except Exception:
            pass
        return info

    def find_ui_element(self, text: str) -> Optional[Dict]:
        """Find a UI element by text, using UI automation first, then OCR."""
        # Try UI automation
        if self._ui_automation:
            try:
                result = self._ui_automation.find_element(text)
                if result:
                    return result
            except Exception:
                pass

        # Fallback to OCR
        if self.screen_monitor:
            try:
                pos = self.screen_monitor.find_text_on_screen(text)
                if pos:
                    return {"text": text, "position": pos, "source": "ocr"}
            except Exception:
                pass

        return None

    def _get_running_processes(self) -> List[str]:
        """Get a list of notable running processes."""
        notable = []
        try:
            if PLATFORM == "Windows":
                import subprocess
                result = subprocess.run(
                    ["tasklist", "/FO", "CSV", "/NH"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    seen = set()
                    for line in result.stdout.strip().split("\n")[:30]:
                        parts = line.strip('"').split('","')
                        if parts:
                            name = parts[0].strip('"')
                            if name not in seen and not name.startswith("svchost"):
                                seen.add(name)
                                notable.append(name)
        except Exception:
            pass
        return notable[:20]

    def get_context_summary(self) -> str:
        """Get a human-readable summary of the current environment."""
        state = self.get_environment_state()
        parts = []

        if state["active_window"]:
            parts.append(f"Active Window: {state['active_window']}")

        if state["window_list"]:
            windows = ", ".join(state["window_list"][:8])
            parts.append(f"Open Windows: {windows}")

        if state["screen_text"]:
            parts.append(f"Screen Content:\n{state['screen_text'][:1000]}")

        return "\n".join(parts) if parts else ""
