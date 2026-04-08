"""
Aura-X UI Automation via pywinauto
Primary system interaction layer — structured, fast, reliable.
Falls back to pyautogui when pywinauto can't access an application.
"""

import time
from typing import Dict, List, Optional, Tuple
from core.logger import setup_logger

logger = setup_logger("aura_x.automation.ui")

try:
    import pywinauto
    from pywinauto import Application, Desktop
    from pywinauto.findwindows import ElementNotFoundError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    logger.info("pywinauto not installed. UI automation will use pyautogui fallback.")


class UIAutomation:
    """
    Structured UI automation using pywinauto.
    Provides window management, element interaction, and state reading.
    """

    def __init__(self):
        self.available = PYWINAUTO_AVAILABLE
        self._desktop = None
        if self.available:
            try:
                self._desktop = Desktop(backend="uia")
            except Exception as e:
                logger.warning(f"Desktop UIA init error: {e}")
                try:
                    self._desktop = Desktop(backend="win32")
                except Exception as e2:
                    logger.warning(f"Desktop Win32 init error: {e2}")
                    self.available = False

    def get_state(self) -> Dict:
        """Get current UI state: active window, open windows, accessible elements."""
        state = {
            "active_window": "",
            "windows": [],
            "elements": []
        }

        if not self.available or not self._desktop:
            return state

        try:
            # Get all visible top-level windows
            windows = self._desktop.windows()
            for win in windows[:20]:
                try:
                    title = win.window_text()
                    if title and title.strip() and len(title) > 1:
                        state["windows"].append(title.strip())
                except Exception:
                    pass

            # Get active/foreground window
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                state["active_window"] = buf.value
            except Exception:
                if state["windows"]:
                    state["active_window"] = state["windows"][0]

        except Exception as e:
            logger.debug(f"UI state error: {e}")

        return state

    def get_active_window_detail(self) -> Dict:
        """Get detailed information about the active window including child elements."""
        info = {"title": "", "process": "", "elements": [], "rect": None}

        if not self.available:
            return info

        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            info["title"] = buf.value

            # Try to connect to the active window
            try:
                app = Application(backend="uia").connect(handle=hwnd)
                window = app.window(handle=hwnd)

                # Get window rectangle
                rect = window.rectangle()
                info["rect"] = {
                    "left": rect.left, "top": rect.top,
                    "right": rect.right, "bottom": rect.bottom
                }

                # Get child elements (limited)
                try:
                    children = window.children()
                    for child in children[:15]:
                        try:
                            elem_info = {
                                "type": child.friendly_class_name(),
                                "text": child.window_text()[:100] if child.window_text() else "",
                                "enabled": child.is_enabled(),
                                "visible": child.is_visible()
                            }
                            if elem_info["text"] or elem_info["type"] in ("Button", "Edit", "ComboBox"):
                                info["elements"].append(elem_info)
                        except Exception:
                            pass
                except Exception:
                    pass

            except Exception:
                pass

        except Exception as e:
            logger.debug(f"Active window detail error: {e}")

        return info

    def find_element(self, text: str) -> Optional[Dict]:
        """Find a UI element by its text content."""
        if not self.available:
            return None

        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            app = Application(backend="uia").connect(handle=hwnd)
            window = app.window(handle=hwnd)

            # Search for elements with matching text
            try:
                element = window.child_window(title_re=f".*{text}.*", found_index=0)
                if element.exists():
                    rect = element.rectangle()
                    center_x = (rect.left + rect.right) // 2
                    center_y = (rect.top + rect.bottom) // 2
                    return {
                        "text": element.window_text(),
                        "type": element.friendly_class_name(),
                        "position": (center_x, center_y),
                        "rect": {"left": rect.left, "top": rect.top,
                                 "right": rect.right, "bottom": rect.bottom},
                        "source": "pywinauto"
                    }
            except ElementNotFoundError:
                pass
            except Exception:
                pass

        except Exception as e:
            logger.debug(f"Element find error: {e}")

        return None

    def click_element(self, text: str) -> bool:
        """Click on a UI element identified by text."""
        element = self.find_element(text)
        if element and element.get("position"):
            try:
                from automation.mouse_keyboard import get_input_automation
                auto = get_input_automation()
                x, y = element["position"]
                return auto.click(x, y)
            except Exception:
                pass
        return False

    def list_windows(self) -> List[Dict]:
        """List all visible windows with details."""
        windows = []
        if not self.available or not self._desktop:
            return windows

        try:
            for win in self._desktop.windows():
                try:
                    title = win.window_text()
                    if title and title.strip():
                        rect = win.rectangle()
                        windows.append({
                            "title": title.strip(),
                            "rect": {
                                "left": rect.left, "top": rect.top,
                                "right": rect.right, "bottom": rect.bottom,
                                "width": rect.right - rect.left,
                                "height": rect.bottom - rect.top
                            },
                            "visible": win.is_visible(),
                            "enabled": win.is_enabled()
                        })
                except Exception:
                    pass
        except Exception:
            pass

        return windows

    def focus_window(self, title: str) -> bool:
        """Bring a window to the foreground by title."""
        if not self.available:
            return False

        try:
            app = Application(backend="uia").connect(title_re=f".*{title}.*")
            dlg = app.top_window()
            dlg.set_focus()
            return True
        except Exception as e:
            logger.debug(f"Focus window error: {e}")
            return False

    def close_window(self, title: str) -> bool:
        """Close a window by title."""
        if not self.available:
            return False

        try:
            app = Application(backend="uia").connect(title_re=f".*{title}.*")
            dlg = app.top_window()
            dlg.close()
            return True
        except Exception as e:
            logger.debug(f"Close window error: {e}")
            return False
