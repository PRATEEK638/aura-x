"""
Aura-X Permission System
GUI-compatible permission checking with auto-approve for safe operations.
"""

import time
from typing import Optional
from core.logger import setup_logger, log_action

logger = setup_logger("aura_x.permissions")

RISK_LEVELS = {
    "safe": 0,
    "moderate": 1,
    "critical": 2
}

TOOL_RISK_MAP = {
    "open_app": "safe",
    "web_scrape": "safe",
    "screen_analyze": "safe",
    "write_code": "safe",
    "create_word_doc": "moderate",
    "create_excel_sheet": "moderate",
    "create_ppt": "moderate",
    "organize_files": "moderate",
    "run_command": "critical",
    "delete_file": "critical",
    "mouse_click": "moderate",
    "keyboard_type": "moderate",
    "office_control": "moderate"
}

AUTO_APPROVE_SAFE = True


class PermissionRequest:
    def __init__(self, tool: str, params: dict, explanation: str):
        self.tool = tool
        self.params = params
        self.explanation = explanation
        self.risk = TOOL_RISK_MAP.get(tool, "moderate")
        self.timestamp = time.time()
        self.approved: Optional[bool] = None
        self.requires_permission = self.risk in ("moderate", "critical")


class PermissionSystem:
    """
    Permission system that works with GUI.
    In interactive mode, auto-approves safe+moderate, logs critical.
    In auto mode, auto-approves everything except critical.
    In strict mode, only auto-approves safe.
    """

    def __init__(self, mode: str = "interactive"):
        self.mode = mode
        self.auto_approve_safe = AUTO_APPROVE_SAFE
        self._history: list = []
        self._gui_callback = None

    def set_gui_callback(self, callback):
        """Set a callback for GUI-based permission dialogs."""
        self._gui_callback = callback

    def request_permission(self, tool: str, params: dict, explanation: str) -> bool:
        req = PermissionRequest(tool, params, explanation)

        # Safe tools are always auto-approved
        if req.risk == "safe" and self.auto_approve_safe:
            req.approved = True
            self._record(req, "auto-approved (safe)")
            return True

        # Auto mode: approve everything except critical
        if self.mode == "auto":
            req.approved = req.risk != "critical"
            self._record(req, f"auto-{'approved' if req.approved else 'denied'} ({req.risk})")
            return req.approved

        # Interactive mode: auto-approve moderate, log it
        if self.mode == "interactive":
            if req.risk == "moderate":
                req.approved = True
                self._record(req, "auto-approved (moderate/interactive)")
                return True
            # Critical: auto-approve in GUI mode (logged), deny in strict
            req.approved = True
            self._record(req, "approved (critical/interactive)")
            logger.warning(f"Critical action approved: {tool} - {explanation}")
            return True

        # Strict mode: deny moderate and critical
        if self.mode == "strict":
            if req.risk == "moderate":
                req.approved = False
                self._record(req, "denied (moderate/strict)")
                return False
            req.approved = False
            self._record(req, "denied (critical/strict)")
            return False

        # Default: approve
        req.approved = True
        self._record(req, "default-approved")
        return True

    def _record(self, req: PermissionRequest, note: str):
        entry = {
            "tool": req.tool,
            "risk": req.risk,
            "approved": req.approved,
            "note": note,
            "explanation": req.explanation
        }
        self._history.append(entry)
        log_action(
            tool=req.tool,
            params=req.params,
            result=note,
            status="approved" if req.approved else "denied",
            risk=req.risk
        )
        if not req.approved:
            logger.info(f"Permission DENIED: {req.tool} [{req.risk}]")
        else:
            logger.debug(f"Permission granted: {req.tool} [{req.risk}]")

    def get_history(self) -> list:
        return self._history.copy()


_permission_system: Optional[PermissionSystem] = None


def get_permission_system() -> PermissionSystem:
    global _permission_system
    if _permission_system is None:
        from core.config import CONFIG
        mode = CONFIG.get("permission_level", "interactive")
        _permission_system = PermissionSystem(mode=mode)
    return _permission_system


def check_permission(tool: str, params: dict, explanation: str) -> bool:
    return get_permission_system().request_permission(tool, params, explanation)
