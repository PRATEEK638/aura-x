from typing import Dict
from core.logger import setup_logger

logger = setup_logger("aura_x.tools.input")


def handle_mouse_click(params: Dict) -> Dict:
    """Click at coordinates or find+click text on screen."""
    from automation.mouse_keyboard import get_input_automation
    auto = get_input_automation()

    if not auto.available:
        return {"status": "error", "error": "Mouse automation not available (pyautogui missing)"}

    # Click by text (OCR-based)
    target_text = params.get("target_text")
    if target_text:
        try:
            from vision.screen_capture import ScreenMonitor
            monitor = ScreenMonitor(interval=0.5, enabled=True)
            monitor._init_ocr()
            import pyautogui
            screenshot = pyautogui.screenshot()
            if monitor._ocr_engine:
                pos = monitor._ocr_engine.find_element_by_text(screenshot, target_text)
                if pos:
                    success = auto.click(pos[0], pos[1])
                    if success:
                        return {"status": "success", "message": f"Clicked on '{target_text}' at {pos}"}
                    return {"status": "error", "error": "Click failed"}
                return {"status": "error", "error": f"Text '{target_text}' not found on screen"}
        except Exception as e:
            return {"status": "error", "error": f"OCR click error: {e}"}

    # Click by coordinates
    x = params.get("x")
    y = params.get("y")
    button = params.get("button", "left")
    clicks = params.get("clicks", 1)

    if x is None or y is None:
        return {"status": "error", "error": "x and y coordinates required"}

    success = auto.click(int(x), int(y), button=button, clicks=int(clicks))
    if success:
        return {"status": "success", "message": f"Clicked {button} at ({x}, {y}) x{clicks}"}
    return {"status": "error", "error": "Click failed"}


def handle_keyboard_type(params: Dict) -> Dict:
    """Type text or press keys."""
    from automation.mouse_keyboard import get_input_automation
    auto = get_input_automation()

    if not auto.available:
        return {"status": "error", "error": "Keyboard automation not available"}

    text = params.get("text")
    key = params.get("key")
    hotkey = params.get("hotkey")  # e.g. ["ctrl", "c"]

    if hotkey:
        if isinstance(hotkey, list):
            success = auto.hotkey(*hotkey)
        else:
            success = auto.hotkey(hotkey)
        return {"status": "success" if success else "error",
                "message": f"Pressed hotkey: {hotkey}" if success else "Hotkey failed"}

    if key:
        success = auto.press_key(key)
        return {"status": "success" if success else "error",
                "message": f"Pressed key: {key}" if success else "Key press failed"}

    if text:
        success = auto.type_text(text)
        preview = text[:50] + "..." if len(text) > 50 else text
        return {"status": "success" if success else "error",
                "message": f"Typed: {preview}" if success else "Type failed"}

    return {"status": "error", "error": "Specify text, key, or hotkey"}


def handle_office_control(params: Dict) -> Dict:
    """High-level Office app control via screen automation."""
    from automation.mouse_keyboard import get_input_automation
    auto = get_input_automation()

    action = params.get("action", "")
    app = params.get("app", "")

    if not action:
        return {"status": "error", "error": "action required"}

    action_lower = action.lower()

    try:
        if action_lower == "save":
            auto.save()
            return {"status": "success", "message": "Saved document (Ctrl+S)"}

        elif action_lower == "close":
            auto.close_window()
            return {"status": "success", "message": "Closed window (Alt+F4)"}

        elif action_lower == "undo":
            auto.undo()
            return {"status": "success", "message": "Undo (Ctrl+Z)"}

        elif action_lower == "select_all":
            auto.select_all()
            return {"status": "success", "message": "Selected all (Ctrl+A)"}

        elif action_lower == "copy":
            auto.copy()
            return {"status": "success", "message": "Copied (Ctrl+C)"}

        elif action_lower == "paste":
            auto.paste()
            return {"status": "success", "message": "Pasted (Ctrl+V)"}

        elif action_lower == "new":
            auto.new_window()
            return {"status": "success", "message": "New document (Ctrl+N)"}

        elif action_lower in ("bold", "italic", "underline"):
            key_map = {"bold": "b", "italic": "i", "underline": "u"}
            auto.hotkey("ctrl", key_map[action_lower])
            return {"status": "success", "message": f"Applied {action_lower}"}

        elif action_lower == "type":
            text = params.get("text", "")
            if text:
                auto.type_text(text)
                return {"status": "success", "message": f"Typed {len(text)} characters"}
            return {"status": "error", "error": "No text to type"}

        elif action_lower == "click_menu":
            menu_item = params.get("menu_item", "")
            if menu_item:
                from vision.screen_capture import ScreenMonitor
                import pyautogui
                monitor = ScreenMonitor(interval=0.5, enabled=True)
                monitor._init_ocr()
                screenshot = pyautogui.screenshot()
                if monitor._ocr_engine:
                    pos = monitor._ocr_engine.find_element_by_text(screenshot, menu_item)
                    if pos:
                        auto.click(pos[0], pos[1])
                        return {"status": "success", "message": f"Clicked menu item: {menu_item}"}
                return {"status": "error", "error": f"Menu item '{menu_item}' not found"}

        else:
            return {"status": "error", "error": f"Unknown office action: {action}"}

    except Exception as e:
        logger.error(f"Office control error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
