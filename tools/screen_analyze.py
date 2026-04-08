"""
Aura-X Screen Analyze Tool
Uses the enhanced OCR engine + screen monitor for real-time screen understanding.
Supports: full analysis, text search, region capture, and clickable element detection.
"""

from typing import Dict
from core.logger import setup_logger

logger = setup_logger("aura_x.tools.screen_analyze")


def handle_screen_analyze(params: Dict) -> Dict:
    """
    Analyze the current screen content.

    Modes:
        full     — Full OCR + layout analysis + clickable elements
        find     — Find specific text on screen (returns position)
        click    — Find text and click on it
        region   — Analyze a specific screen region
        summary  — Quick summary (active window + key text)
    """
    mode = params.get("mode", "full").lower()

    try:
        import pyautogui
    except ImportError:
        return {"status": "error", "error": "pyautogui not installed — screen capture unavailable"}

    try:
        from vision.ocr_engine import OCREngine
        ocr = OCREngine()
    except Exception as e:
        return {"status": "error", "error": f"OCR engine error: {e}"}

    # ─── Get active window title ───
    active_window = ""
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        active_window = buf.value
    except Exception:
        pass

    # ─── Capture screenshot ───
    if mode == "region":
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        w = int(params.get("width", 400))
        h = int(params.get("height", 300))
        try:
            screenshot = pyautogui.screenshot(region=(x, y, w, h))
        except Exception as e:
            return {"status": "error", "error": f"Region capture failed: {e}"}
    else:
        try:
            screenshot = pyautogui.screenshot()
        except Exception as e:
            return {"status": "error", "error": f"Screenshot failed: {e}"}

    # ─── Find text mode ───
    if mode == "find":
        target = params.get("target_text", params.get("text", ""))
        if not target:
            return {"status": "error", "error": "target_text required for find mode"}

        pos = ocr.find_text_position(screenshot, target)
        if pos:
            return {
                "status": "success",
                "message": f"Found '{target}' at position ({pos[0]}, {pos[1]})",
                "position": {"x": pos[0], "y": pos[1]},
                "found": True
            }
        return {
            "status": "success",
            "message": f"Text '{target}' not found on screen",
            "found": False
        }

    # ─── Click text mode ───
    if mode == "click":
        target = params.get("target_text", params.get("text", ""))
        if not target:
            return {"status": "error", "error": "target_text required for click mode"}

        pos = ocr.find_text_position(screenshot, target)
        if pos:
            try:
                pyautogui.click(pos[0], pos[1])
                return {
                    "status": "success",
                    "message": f"Clicked on '{target}' at ({pos[0]}, {pos[1]})",
                    "position": {"x": pos[0], "y": pos[1]}
                }
            except Exception as e:
                return {"status": "error", "error": f"Click failed: {e}"}
        return {
            "status": "error",
            "message": f"Text '{target}' not found on screen — cannot click"
        }

    # ─── Summary mode ───
    if mode == "summary":
        text = ocr.extract_text(screenshot)
        preview = text[:500] if text else "(no text detected)"
        return {
            "status": "success",
            "message": f"Active Window: {active_window}\nScreen: {screenshot.width}x{screenshot.height}\n\nVisible text:\n{preview}",
            "active_window": active_window,
            "text_preview": preview,
            "ocr_available": ocr.is_available()
        }

    # ─── Full analysis mode ───
    text = ocr.extract_text(screenshot)
    layout = ocr.analyze_screen_layout(screenshot)
    clickable = ocr.get_clickable_elements(screenshot)

    # Build comprehensive summary
    summary_parts = [
        f"📺 Active Window: {active_window}",
        f"📐 Screen: {screenshot.width}x{screenshot.height}",
    ]

    if layout.get("layout"):
        l = layout["layout"]
        ui_parts = []
        if l.get("has_toolbar"):
            ui_parts.append("toolbar")
        if l.get("has_sidebar"):
            ui_parts.append("sidebar")
        if l.get("has_statusbar"):
            ui_parts.append("status bar")
        if ui_parts:
            summary_parts.append(f"🏗 Layout: {', '.join(ui_parts)}")

    if clickable:
        btn_names = [e["text"] for e in clickable[:15]]
        summary_parts.append(f"🖱 Clickable elements ({len(clickable)}): {', '.join(btn_names)}")

    if text:
        summary_parts.append(f"\n📝 Visible text:\n{text[:1000]}")
    else:
        summary_parts.append("\n⚠ No text detected (OCR may not be available)")

    return {
        "status": "success",
        "message": "\n".join(summary_parts),
        "active_window": active_window,
        "screen_size": f"{screenshot.width}x{screenshot.height}",
        "ocr_text": text,
        "clickable_elements": [
            {"text": e["text"], "x": e["center_x"], "y": e["center_y"]}
            for e in clickable
        ],
        "layout": layout.get("layout", {}),
        "ocr_available": ocr.is_available()
    }
