"""
Aura-X Tool Executor — V5
Central dispatcher that routes ALL tool calls.
Includes file operations, app control, and UI automation.
"""

import os
import subprocess
from typing import Dict, Any
from core.logger import setup_logger

logger = setup_logger("aura_x.tools.executor")


class ToolExecutor:
    """Central dispatcher for all Aura-X tools."""

    PERMISSION_REQUIRED = {
        "run_command":        ("critical", "Run a system command"),
        "organize_files":     ("moderate", "Organize and move files"),
        "write_code":         ("moderate", "Create or modify files"),
        "mouse_click":        ("moderate", "Click on your screen"),
        "keyboard_type":      ("moderate", "Type on your keyboard"),
        "office_control":     ("moderate", "Control Office applications"),
        "create_word_doc":    ("moderate", "Create a Word document"),
        "create_excel_sheet": ("moderate", "Create an Excel spreadsheet"),
        "create_ppt":         ("moderate", "Create a PowerPoint presentation"),
        "desktop_action":     ("moderate", "Perform a desktop action"),
        "file_operation":     ("moderate", "Perform file operations"),
        "app_control":        ("moderate", "Control an application window"),
    }

    SAFE_TOOLS = {"open_app", "screen_analyze", "web_scrape", "find_files", "list_files",
                  "read_file", "app_info", "system_info"}

    def __init__(self):
        self._registry: Dict[str, callable] = {}
        self._permission_callback = None
        self._load_tools()

    def set_permission_callback(self, callback):
        self._permission_callback = callback

    def _load_tools(self):
        from tools.open_app import handle_open_app
        from tools.organize_files import handle_organize_files
        from tools.run_command import handle_run_command
        from tools.write_code import handle_write_code
        from tools.screen_analyze import handle_screen_analyze
        from tools.mouse_keyboard import handle_mouse_click, handle_keyboard_type, handle_office_control
        from tools.office_tools import handle_create_word, handle_create_excel, handle_create_ppt

        # ── Web scrape ──────────────────────────────────────────────
        def handle_web_scrape(params: Dict[str, Any]) -> Dict[str, Any]:
            from web.scraper import WebScraper
            scraper = WebScraper(timeout=int(params.get("timeout", 15)))
            action = str(params.get("action", "summary")).lower()
            if action == "search":
                return scraper.search_web(params.get("query", ""))
            url = params.get("url", "")
            if not url:
                return {"status": "error", "error": "url is required"}
            dispatch = {"summary": scraper.scrape_summary, "full": scraper.scrape_full,
                        "links": scraper.extract_links, "tables": scraper.extract_tables}
            if action == "json":
                return scraper.fetch_json(url, params=params.get("params"))
            if action in dispatch:
                return dispatch[action](url)
            return {"status": "error", "error": f"Unknown action: {action}"}

        # ── Desktop action (folders, close apps, list windows) ──────
        def handle_desktop_action(params: Dict[str, Any]) -> Dict[str, Any]:
            action = params.get("action", "").lower()

            if action == "open_folder":
                path = params.get("path", "")
                if path and os.path.exists(path):
                    subprocess.Popen(["explorer", path])
                    return {"status": "success", "message": f"Opened folder: {path}"}
                return {"status": "error", "error": f"Folder not found: {path}"}

            elif action == "create_folder":
                path = params.get("path", "")
                if path:
                    os.makedirs(path, exist_ok=True)
                    subprocess.Popen(["explorer", path])
                    return {"status": "success", "message": f"Created: {path}"}
                return {"status": "error", "error": "No path specified"}

            elif action == "close_app":
                name = params.get("name", "")
                if name:
                    # Add .exe if not present
                    if not name.endswith(".exe"):
                        name += ".exe"
                    try:
                        subprocess.run(["taskkill", "/IM", name, "/F"],
                                       capture_output=True, timeout=5)
                        return {"status": "success", "message": f"Closed: {name}"}
                    except Exception as e:
                        return {"status": "error", "error": str(e)}
                return {"status": "error", "error": "No app name specified"}

            elif action == "list_windows":
                try:
                    from automation.ui_automation import UIAutomation
                    ui = UIAutomation()
                    wins = ui.list_windows()
                    if wins:
                        lines = [f"• {w['title']}" for w in wins[:25]]
                        return {"status": "success",
                                "message": f"Open windows ({len(wins)}):\n" + "\n".join(lines),
                                "windows": [w['title'] for w in wins]}
                    return {"status": "success", "message": "No windows found"}
                except Exception as e:
                    return {"status": "error", "error": str(e)}

            elif action in ("list_files", "ls"):
                path = params.get("path", "")
                if path and os.path.exists(path):
                    items = []
                    for item in sorted(os.listdir(path)):
                        full = os.path.join(path, item)
                        is_dir = os.path.isdir(full)
                        size = os.path.getsize(full) if os.path.isfile(full) else 0
                        items.append(f"{'📁' if is_dir else '📄'} {item}" +
                                     (f" ({_human_size(size)})" if size else ""))
                    return {"status": "success",
                            "message": f"Contents of {path}:\n" + "\n".join(items[:50]),
                            "items": items}
                return {"status": "error", "error": f"Path not found: {path}"}

            elif action == "delete_file":
                path = params.get("path", "")
                if path and os.path.exists(path):
                    if os.path.isfile(path):
                        os.remove(path)
                        return {"status": "success", "message": f"Deleted: {path}"}
                    elif os.path.isdir(path):
                        import shutil
                        shutil.rmtree(path)
                        return {"status": "success", "message": f"Deleted folder: {path}"}
                return {"status": "error", "error": f"Path not found: {path}"}

            return {"status": "error", "error": f"Unknown action: {action}"}

        # ── File operations (copy, move, rename, find, read) ────────
        def handle_file_operation(params: Dict[str, Any]) -> Dict[str, Any]:
            from automation.file_system import (
                copy_file, rename_file, find_files, read_text_file,
                write_text_file, get_directory_stats, delete_file_or_dir
            )
            action = params.get("action", "").lower()

            if action == "copy":
                return copy_file(params.get("source", ""), params.get("destination", ""))
            elif action == "move":
                src = params.get("source", "")
                dst = params.get("destination", "")
                if src and dst and os.path.exists(src):
                    import shutil
                    os.makedirs(os.path.dirname(dst) or dst, exist_ok=True)
                    shutil.move(src, dst)
                    return {"status": "success", "message": f"Moved: {src} → {dst}"}
                return {"status": "error", "error": "Source not found or missing destination"}
            elif action == "rename":
                return rename_file(params.get("path", ""), params.get("new_name", ""))
            elif action == "find":
                results = find_files(
                    params.get("path", str(os.path.expanduser("~"))),
                    params.get("pattern", "*"),
                    params.get("category"),
                    params.get("min_size"),
                    params.get("max_size")
                )
                if results:
                    lines = [f"📄 {r['name']} ({r.get('size_human', '')}) — {r['path']}"
                             for r in results[:20]]
                    return {"status": "success",
                            "message": f"Found {len(results)} files:\n" + "\n".join(lines),
                            "results": results[:20]}
                return {"status": "success", "message": "No files found matching criteria"}
            elif action == "read":
                return read_text_file(params.get("path", ""))
            elif action == "write":
                return write_text_file(params.get("path", ""), params.get("content", ""),
                                       append=params.get("append", False))
            elif action == "stats":
                return get_directory_stats(params.get("path", ""))
            elif action == "delete":
                return delete_file_or_dir(params.get("path", ""), safe=params.get("safe", True))
            else:
                return {"status": "error",
                        "error": f"Unknown file action: {action}. Use: copy, move, rename, find, read, write, stats, delete"}

        # ── App control (focus, interact with windows) ──────────────
        def handle_app_control(params: Dict[str, Any]) -> Dict[str, Any]:
            action = params.get("action", "").lower()
            target = params.get("target", params.get("window", params.get("app", "")))

            try:
                from automation.ui_automation import UIAutomation
                ui = UIAutomation()
            except Exception as e:
                return {"status": "error", "error": f"UI automation unavailable: {e}"}

            if action == "focus":
                if ui.focus_window(target):
                    return {"status": "success", "message": f"Focused window: {target}"}
                return {"status": "error", "error": f"Window not found: {target}"}

            elif action == "close":
                if ui.close_window(target):
                    return {"status": "success", "message": f"Closed window: {target}"}
                return {"status": "error", "error": f"Window not found: {target}"}

            elif action == "inspect":
                info = ui.get_active_window_detail()
                if info.get("title"):
                    parts = [f"Window: {info['title']}"]
                    if info.get("elements"):
                        parts.append(f"UI elements ({len(info['elements'])}):")
                        for e in info["elements"][:15]:
                            text = e.get("text", "")
                            etype = e.get("type", "")
                            if text:
                                parts.append(f"  [{etype}] {text}")
                            elif etype in ("Button", "Edit", "ComboBox", "CheckBox"):
                                parts.append(f"  [{etype}] (no label)")
                    return {"status": "success", "message": "\n".join(parts)}
                return {"status": "error", "error": "No active window detected"}

            elif action == "click_element":
                text = params.get("text", params.get("element", ""))
                if text:
                    if ui.click_element(text):
                        return {"status": "success", "message": f"Clicked element: {text}"}
                    return {"status": "error", "error": f"Element not found: {text}"}
                return {"status": "error", "error": "No element text specified"}

            elif action == "list_elements":
                info = ui.get_active_window_detail()
                elems = info.get("elements", [])
                if elems:
                    lines = [f"[{e.get('type','')}] {e.get('text','(no text)')}" for e in elems]
                    return {"status": "success",
                            "message": f"Elements in {info.get('title','')}:\n" + "\n".join(lines)}
                return {"status": "success", "message": "No accessible elements found"}

            elif action == "type_in":
                # Focus window then type text
                text = params.get("text", "")
                if target:
                    ui.focus_window(target)
                    import time; time.sleep(0.3)
                if text:
                    from automation.mouse_keyboard import get_input_automation
                    auto = get_input_automation()
                    auto.type_text(text)
                    return {"status": "success", "message": f"Typed into {target or 'active window'}"}
                return {"status": "error", "error": "No text specified"}

            return {"status": "error",
                    "error": f"Unknown app action: {action}. Use: focus, close, inspect, click_element, list_elements, type_in"}

        # ── System info ─────────────────────────────────────────────
        def handle_system_info(params: Dict[str, Any]) -> Dict[str, Any]:
            import platform
            info = params.get("type", "general").lower()
            try:
                if info == "general":
                    import psutil
                    mem = psutil.virtual_memory()
                    disk = psutil.disk_usage("C:\\")
                    return {"status": "success", "message":
                        f"System: {platform.system()} {platform.release()}\n"
                        f"CPU: {psutil.cpu_percent()}% used ({psutil.cpu_count()} cores)\n"
                        f"RAM: {mem.percent}% used ({_human_size(mem.used)}/{_human_size(mem.total)})\n"
                        f"Disk C: {disk.percent}% used ({_human_size(disk.used)}/{_human_size(disk.total)})"}
                elif info == "processes":
                    result = subprocess.run(
                        ["tasklist", "/FO", "CSV", "/NH"],
                        capture_output=True, text=True, timeout=5
                    )
                    lines = []
                    seen = set()
                    for line in result.stdout.strip().split("\n")[:30]:
                        parts = line.strip('"').split('","')
                        if parts and parts[0] not in seen:
                            seen.add(parts[0])
                            lines.append(parts[0])
                    return {"status": "success", "message": "Running processes:\n" + "\n".join(f"• {p}" for p in lines)}
            except ImportError:
                return {"status": "success", "message":
                    f"System: {platform.system()} {platform.release()} {platform.machine()}\n"
                    f"(Install psutil for detailed stats: pip install psutil)"}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        # ═══════════ Register all tools ═══════════════════════════════
        self._registry = {
            # Core tools
            "open_app":           handle_open_app,
            "organize_files":     handle_organize_files,
            "run_command":        handle_run_command,
            "write_code":         handle_write_code,
            "screen_analyze":     handle_screen_analyze,

            # Input automation
            "mouse_click":        handle_mouse_click,
            "keyboard_type":      handle_keyboard_type,
            "office_control":     handle_office_control,

            # Office creation
            "create_word_doc":    handle_create_word,
            "create_excel_sheet": handle_create_excel,
            "create_ppt":         handle_create_ppt,

            # Web
            "web_scrape":         handle_web_scrape,

            # Desktop & files
            "desktop_action":     handle_desktop_action,
            "file_operation":     handle_file_operation,

            # App window control (NEW)
            "app_control":        handle_app_control,

            # System (NEW)
            "system_info":        handle_system_info,
        }

        logger.info(f"Loaded {len(self._registry)} tools")

    def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict:
        if tool_name not in self._registry:
            return {"status": "error",
                    "error": f"Unknown tool: '{tool_name}'. Available: {list(self._registry.keys())}"}

        # Check permissions
        if tool_name in self.PERMISSION_REQUIRED and tool_name not in self.SAFE_TOOLS:
            risk, explanation = self.PERMISSION_REQUIRED[tool_name]
            specific = self._build_explanation(tool_name, params, explanation)
            if risk == "critical":
                if self._permission_callback:
                    allowed = self._permission_callback(tool_name, params, specific, risk)
                    if not allowed:
                        return {"status": "denied", "message": f"Permission denied: {specific}"}
                else:
                    logger.warning(f"No permission callback — auto-allowing: {tool_name}")

        try:
            handler = self._registry[tool_name]
            result = handler(params)
            if not isinstance(result, dict):
                result = {"status": "success", "message": str(result)}
            self._post_execute_feedback(tool_name, params, result)
            return result
        except Exception as e:
            logger.error(f"Tool '{tool_name}' error: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    def _build_explanation(self, tool: str, params: dict, base: str) -> str:
        if tool == "run_command":
            return f"Run command: {params.get('command', 'unknown')}"
        elif tool == "organize_files":
            return f"Organize files in: {params.get('path', 'unknown')}"
        elif tool == "file_operation":
            return f"File {params.get('action', 'unknown')}: {params.get('path', params.get('source', ''))}"
        elif tool == "app_control":
            return f"App control: {params.get('action', 'unknown')} on {params.get('target', '')}"
        return base

    def _post_execute_feedback(self, tool: str, params: dict, result: dict):
        if result.get("status") != "success":
            return
        if tool == "write_code":
            filepath = params.get("filepath", "")
            if filepath and os.path.exists(filepath):
                try:
                    subprocess.Popen(["explorer", "/select,", filepath])
                except Exception:
                    pass
        elif tool in ("create_word_doc", "create_excel_sheet", "create_ppt"):
            filepath = result.get("filepath", "")
            if filepath and os.path.exists(filepath):
                try:
                    os.startfile(filepath)
                except Exception:
                    pass

    def list_tools(self) -> list:
        return list(self._registry.keys())


def _human_size(size_bytes) -> str:
    size_bytes = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
