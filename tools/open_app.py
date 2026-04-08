"""
Aura-X — Open App / URL Tool
"""

import subprocess
import platform
import webbrowser
import os
import re
from typing import Dict
from core.logger import setup_logger

logger = setup_logger("aura_x.tools.open_app")

PLATFORM = platform.system()

APP_MAP_WINDOWS = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "powerpoint": r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
    "paint": "mspaint.exe",
    "vlc": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    "spotify": os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
    "vscode": os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
    "code": os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
    "settings": "ms-settings:",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "snipping tool": "snippingtool.exe",
    "photos": "ms-photos:",
    "store": "ms-windows-store:",
}

WEB_SHORTCUTS = {
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "google": "https://www.google.com",
    "github": "https://www.github.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://www.twitter.com",
    "x": "https://www.x.com",
    "linkedin": "https://www.linkedin.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "whatsapp": "https://web.whatsapp.com",
    "chatgpt": "https://chat.openai.com",
    "stackoverflow": "https://stackoverflow.com",
}


def _is_url(text: str) -> bool:
    return bool(re.match(r'^https?://', text)) or bool(re.match(r'^www\.', text))


def handle_open_app(params: Dict) -> Dict:
    """Open an app, URL, or web shortcut."""
    # Accept 'name', 'app', 'url', or 'target' — LLMs use different keys
    target = (params.get("name") or params.get("app") or
              params.get("url") or params.get("target", "")).strip()

    if not target:
        return {"status": "error", "error": "No app or URL specified"}

    # Handle URL
    if _is_url(target):
        url = target if target.startswith("http") else f"https://{target}"
        try:
            webbrowser.open(url)
            return {"status": "success", "message": f"Opened URL: {url}"}
        except Exception as e:
            return {"status": "error", "error": f"Failed to open URL: {e}"}

    # Handle web shortcuts
    target_lower = target.lower().strip()
    if target_lower in WEB_SHORTCUTS:
        url = WEB_SHORTCUTS[target_lower]
        webbrowser.open(url)
        return {"status": "success", "message": f"Opened {target_lower} in browser"}

    # Platform-specific app launch
    try:
        if PLATFORM == "Windows":
            return _open_windows(target_lower, target)
        elif PLATFORM == "Darwin":
            return _open_mac(target_lower)
        else:
            return _open_linux(target_lower)
    except Exception as e:
        logger.error(f"App launch error: {e}")
        return {"status": "error", "error": str(e)}


def _open_windows(target_lower: str, original: str) -> Dict:
    # Try known app map
    app_path = APP_MAP_WINDOWS.get(target_lower)
    if app_path:
        # Handle ms-* protocol URIs
        if app_path.startswith("ms-"):
            try:
                os.startfile(app_path)
                return {"status": "success", "message": f"Launched {original}"}
            except Exception:
                pass
        # Handle exe paths
        try:
            if os.path.exists(app_path):
                subprocess.Popen([app_path])
                return {"status": "success", "message": f"Launched {original}"}
        except Exception:
            pass

    # Try 'start' command (works for most Windows apps)
    try:
        subprocess.Popen(["start", "", target_lower], shell=True)
        return {"status": "success", "message": f"Launched {original}"}
    except Exception as e:
        return {"status": "error", "error": f"Could not open {original}: {e}"}


def _open_mac(target: str) -> Dict:
    try:
        result = subprocess.run(
            ["open", "-a", target.title()],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return {"status": "success", "message": f"Launched {target}"}
        return {"status": "error", "error": f"App not found: {target}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _open_linux(target: str) -> Dict:
    try:
        subprocess.Popen([target], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"status": "success", "message": f"Launched {target}"}
    except FileNotFoundError:
        try:
            subprocess.Popen(["xdg-open", target])
            return {"status": "success", "message": f"Opened {target}"}
        except Exception as e:
            return {"status": "error", "error": f"Could not open {target}: {e}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
