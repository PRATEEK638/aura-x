import time
import threading
from typing import Optional, Tuple, List
from core.logger import setup_logger

logger = setup_logger("aura_x.automation.input")

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logger.warning("pyautogui not available. Mouse/keyboard automation disabled.")

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False


class InputAutomation:
    def __init__(self):
        self.available = PYAUTOGUI_AVAILABLE
        self._action_history: List[dict] = []
        self._mouse_state = {"x": 0, "y": 0, "buttons": {}}
        self._keyboard_state = {"held_keys": set()}

        if self.available:
            self._update_mouse_state()

    def _update_mouse_state(self):
        try:
            pos = pyautogui.position()
            self._mouse_state["x"] = pos.x
            self._mouse_state["y"] = pos.y
        except Exception:
            pass

    def _record_action(self, action_type: str, details: dict):
        self._action_history.append({
            "type": action_type,
            "details": details,
            "timestamp": time.time()
        })
        if len(self._action_history) > 200:
            self._action_history = self._action_history[-200:]

    def click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.1,
        smooth: bool = True
    ) -> bool:
        if not self.available:
            return False
        try:
            if x is not None and y is not None:
                screen_w, screen_h = pyautogui.size()
                x = max(0, min(x, screen_w - 1))
                y = max(0, min(y, screen_h - 1))
                if smooth:
                    pyautogui.moveTo(x, y, duration=0.3, tween=pyautogui.easeInOutQuad)
                    time.sleep(0.05)
                pyautogui.click(x, y, button=button, clicks=clicks, interval=interval)
            else:
                pyautogui.click(button=button, clicks=clicks, interval=interval)

            self._update_mouse_state()
            self._record_action("click", {"x": x, "y": y, "button": button, "clicks": clicks})
            return True
        except pyautogui.FailSafeException:
            logger.error("Failsafe triggered!")
            return False
        except Exception as e:
            logger.error(f"Click error: {e}")
            return False

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        return self.click(x, y, clicks=2, interval=0.1)

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        return self.click(x, y, button="right")

    def move_to(self, x: int, y: int, duration: float = 0.3) -> bool:
        if not self.available:
            return False
        try:
            pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeInOutQuad)
            self._update_mouse_state()
            return True
        except Exception as e:
            logger.error(f"Move error: {e}")
            return False

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int,
             duration: float = 0.5, button: str = "left") -> bool:
        if not self.available:
            return False
        try:
            pyautogui.moveTo(start_x, start_y, duration=0.2)
            time.sleep(0.05)
            pyautogui.dragTo(end_x, end_y, duration=duration, button=button,
                             tween=pyautogui.easeInOutQuad)
            self._record_action("drag", {"from": (start_x, start_y), "to": (end_x, end_y)})
            return True
        except Exception as e:
            logger.error(f"Drag error: {e}")
            return False

    def scroll(self, amount: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        if not self.available:
            return False
        try:
            if x and y:
                pyautogui.moveTo(x, y, duration=0.2)
            pyautogui.scroll(amount)
            self._record_action("scroll", {"amount": amount, "x": x, "y": y})
            return True
        except Exception as e:
            logger.error(f"Scroll error: {e}")
            return False

    def type_text(self, text: str, interval: float = 0.03, use_clipboard: bool = True) -> bool:
        if not self.available:
            return False
        try:
            if use_clipboard and CLIPBOARD_AVAILABLE and len(text) > 10:
                original_clip = ""
                try:
                    original_clip = pyperclip.paste()
                except Exception:
                    pass
                pyperclip.copy(text)
                time.sleep(0.1)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.1)
                try:
                    pyperclip.copy(original_clip)
                except Exception:
                    pass
            else:
                pyautogui.typewrite(text, interval=interval)

            self._record_action("type", {"text": text[:50] + "..." if len(text) > 50 else text})
            return True
        except Exception as e:
            logger.error(f"Type error: {e}")
            return False

    def press_key(self, key: str) -> bool:
        if not self.available:
            return False
        try:
            pyautogui.press(key)
            self._record_action("press", {"key": key})
            return True
        except Exception as e:
            logger.error(f"Press key error: {e}")
            return False

    def hotkey(self, *keys: str) -> bool:
        if not self.available:
            return False
        try:
            pyautogui.hotkey(*keys)
            self._record_action("hotkey", {"keys": list(keys)})
            return True
        except Exception as e:
            logger.error(f"Hotkey error: {e}")
            return False

    def key_down(self, key: str) -> bool:
        if not self.available:
            return False
        try:
            pyautogui.keyDown(key)
            self._keyboard_state["held_keys"].add(key)
            return True
        except Exception as e:
            logger.error(f"Key down error: {e}")
            return False

    def key_up(self, key: str) -> bool:
        if not self.available:
            return False
        try:
            pyautogui.keyUp(key)
            self._keyboard_state["held_keys"].discard(key)
            return True
        except Exception as e:
            logger.error(f"Key up error: {e}")
            return False

    def release_all_keys(self):
        for key in list(self._keyboard_state["held_keys"]):
            self.key_up(key)

    def get_mouse_position(self) -> Tuple[int, int]:
        if not self.available:
            return (0, 0)
        try:
            pos = pyautogui.position()
            return (pos.x, pos.y)
        except Exception:
            return (0, 0)

    def get_screen_size(self) -> Tuple[int, int]:
        if not self.available:
            return (1920, 1080)
        try:
            return pyautogui.size()
        except Exception:
            return (1920, 1080)

    def select_all(self) -> bool:
        return self.hotkey("ctrl", "a")

    def copy(self) -> bool:
        return self.hotkey("ctrl", "c")

    def paste(self) -> bool:
        return self.hotkey("ctrl", "v")

    def undo(self) -> bool:
        return self.hotkey("ctrl", "z")

    def save(self) -> bool:
        return self.hotkey("ctrl", "s")

    def close_window(self) -> bool:
        return self.hotkey("alt", "f4")

    def new_window(self) -> bool:
        return self.hotkey("ctrl", "n")

    def get_clipboard_text(self) -> str:
        if not CLIPBOARD_AVAILABLE:
            return ""
        try:
            return pyperclip.paste()
        except Exception:
            return ""

    def set_clipboard_text(self, text: str):
        if CLIPBOARD_AVAILABLE:
            try:
                pyperclip.copy(text)
            except Exception as e:
                logger.error(f"Clipboard error: {e}")

    def get_action_history(self) -> List[dict]:
        return self._action_history.copy()


_input_automation: Optional[InputAutomation] = None


def get_input_automation() -> InputAutomation:
    global _input_automation
    if _input_automation is None:
        _input_automation = InputAutomation()
    return _input_automation
