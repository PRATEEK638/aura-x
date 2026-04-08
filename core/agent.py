"""
Aura-X Agent Loop
Observe → Understand → Plan → Execute → Verify → Adapt
Optimised: simple tasks skip the full loop, complex tasks get multi-step planning.
"""

import time
import json
import re
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from core.config import CONFIG
from core.logger import setup_logger

logger = setup_logger("aura_x.core.agent")

AGENT_CONFIG = CONFIG.get("agent", {})

# ── Quick-match patterns (resolved WITHOUT an AI call) ──────────────────
QUICK_PATTERNS = [
    # ── Specific multi-word patterns first ──
    # List windows
    (r'\b(?:list|show)\s+(?:all\s+)?(?:open\s+)?windows\b', lambda m: {
        "tool": "desktop_action", "params": {"action": "list_windows"},
        "explanation": "List open windows"}),

    # System info
    (r'\b(?:system\s+(?:info|status)|cpu\s+usage|ram\s+usage|disk\s+usage)\b', lambda m: {
        "tool": "system_info", "params": {"type": "general"},
        "explanation": "Get system information"}),

    # Screenshot
    (r'\b(?:screenshot|capture\s+screen|take\s+screenshot)\b', lambda m: {
        "tool": "screen_analyze", "params": {"mode": "full"},
        "explanation": "Capture and analyze the current screen"}),

    # Type text
    (r'\btype\s+["\'](.+?)["\']', lambda m: {
        "tool": "keyboard_type", "params": {"text": m.group(1)},
        "explanation": f"Type: {m.group(1)[:50]}"}),

    # Organize files
    (r'\borganize\s+(?:files?\s+(?:in|on|at)\s+)?(.+)', lambda m: {
        "tool": "organize_files", "params": {"path": _resolve_path(m.group(1).strip()), "mode": "smart"},
        "explanation": f"Organize files in {m.group(1).strip()}"}),

    # List files
    (r'\b(?:list|show|what.?s in|whats in)\s+(?:files?\s+(?:in|on|at)\s+)?(.+)', lambda m: {
        "tool": "desktop_action", "params": {"action": "list_files", "path": _resolve_path(m.group(1).strip())},
        "explanation": f"List files in {m.group(1).strip()}"}),

    # ── Generic single-word patterns last ──
    # Close app
    (r'\b(?:close|exit|quit)\s+(\S+)', lambda m: {
        "tool": "app_control", "params": {"action": "close", "target": m.group(1)},
        "explanation": f"Close {m.group(1)}"}),

    # Focus/switch
    (r'\b(?:focus|switch\s+to|go\s+to|bring\s+up)\s+(\S+)', lambda m: {
        "tool": "app_control", "params": {"action": "focus", "target": m.group(1)},
        "explanation": f"Focus {m.group(1)}"}),

    # Open app (MOST GENERIC — last)
    (r'\b(?:open|launch|start)\s+(\S+)', lambda m: {
        "tool": "open_app", "params": {"name": m.group(1)},
        "explanation": f"Open {m.group(1)}"}),
]


def _resolve_path(text: str) -> str:
    """Resolve common path aliases to real paths."""
    import os
    text_lower = text.lower().strip().rstrip('.')
    home = os.path.expanduser("~")
    aliases = {
        "desktop": os.path.join(home, "Desktop"),
        "my desktop": os.path.join(home, "Desktop"),
        "the desktop": os.path.join(home, "Desktop"),
        "downloads": os.path.join(home, "Downloads"),
        "my downloads": os.path.join(home, "Downloads"),
        "documents": os.path.join(home, "Documents"),
        "my documents": os.path.join(home, "Documents"),
        "pictures": os.path.join(home, "Pictures"),
        "videos": os.path.join(home, "Videos"),
        "music": os.path.join(home, "Music"),
        "home": home,
        "my folder": home,
    }
    for alias, path in aliases.items():
        if text_lower == alias or text_lower.endswith(alias):
            return path
    return text


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AgentStep:
    id: int
    description: str
    tool: str = ""
    params: Dict = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    retries: int = 0


@dataclass
class AgentTask:
    goal: str
    steps: List[AgentStep] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    created_at: float = field(default_factory=time.time)
    result_summary: str = ""


class AgentLoop:
    """
    Autonomous agent loop.
    Fast path: pattern-match → execute (no AI call).
    Normal path: single AI call → extract tools → execute.
    """

    def __init__(self, ai_router, tool_executor, memory_manager, perception=None):
        self.ai_router = ai_router
        self.tool_executor = tool_executor
        self.memory_manager = memory_manager
        self.perception = perception

        self.max_retries = AGENT_CONFIG.get("max_retries", 2)
        self._running = False
        self._cancelled = False

        # Callbacks for GUI
        self._on_step_start: Optional[Callable] = None
        self._on_step_complete: Optional[Callable] = None
        self._on_task_complete: Optional[Callable] = None
        self._on_thinking: Optional[Callable] = None

    def set_callbacks(self, **kwargs):
        for key, val in kwargs.items():
            attr = f"_{key}"
            if hasattr(self, attr):
                setattr(self, attr, val)

    # ── Main entry ──────────────────────────────────────────────────────
    def process_input(self, user_text: str, screen_context: str = "") -> str:
        self._running = True
        self._cancelled = False

        try:
            # 1) Try quick pattern match (zero AI calls)
            quick = self._quick_match(user_text)
            if quick:
                self._emit_thinking("Executing...")
                task = AgentTask(goal=user_text)
                for i, call in enumerate(quick):
                    step = AgentStep(id=i, description=call["explanation"],
                                    tool=call["tool"], params=call["params"])
                    task.steps.append(step)
                    self._execute_step(step)
                return self._compile_result(task, user_text)

            # 2) Single AI call with tool instructions baked in
            self._emit_thinking("Thinking...")
            messages = self.memory_manager.get_context_messages(
                system_prompt=SYSTEM_PROMPT,
                screen_context=screen_context
            )
            response = self.ai_router.route_and_respond(
                text=user_text, messages=messages, screen_context=screen_context
            )

            # 3) Extract & execute any tool calls from the response
            tool_calls = self._extract_tool_calls(response)
            if tool_calls:
                task = AgentTask(goal=user_text)
                for i, call in enumerate(tool_calls):
                    step = AgentStep(
                        id=i,
                        description=call.get("explanation", f"Execute {call['tool']}"),
                        tool=call["tool"],
                        params=call.get("params", {})
                    )
                    task.steps.append(step)
                    self._execute_step(step)
                    # Retry once on failure
                    if step.status == StepStatus.FAILED and step.retries < self.max_retries:
                        step.retries += 1
                        self._execute_step(step)

                # Strip tool JSON from the conversational part
                clean = self._strip_tool_blocks(response)
                step_summary = self._step_summary(task)
                if clean.strip():
                    return f"{clean}\n\n{step_summary}"
                return step_summary

            # 4) Pure conversation — return as-is
            return response

        except Exception as e:
            logger.error(f"Agent loop error: {e}", exc_info=True)
            return f"I encountered an error: {e}"
        finally:
            self._running = False

    def cancel(self):
        self._cancelled = True

    # ── Quick pattern matching (no AI) ──────────────────────────────────
    def _quick_match(self, text: str) -> Optional[List[dict]]:
        text_lower = text.lower().strip()
        for pattern, handler in QUICK_PATTERNS:
            m = re.search(pattern, text_lower, re.IGNORECASE)
            if m:
                return [handler(m)]
        return None

    # ── Step execution ──────────────────────────────────────────────────
    def _execute_step(self, step: AgentStep):
        step.status = StepStatus.RUNNING
        if self._on_step_start:
            self._on_step_start(step)
        try:
            result = self.tool_executor.execute(step.tool, step.params)
            if result.get("status") == "success":
                step.status = StepStatus.SUCCESS
                step.result = result.get("message", "Done")
            else:
                step.status = StepStatus.FAILED
                step.error = result.get("error", "Unknown error")
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
        if self._on_step_complete:
            self._on_step_complete(step)

    # ── Results ─────────────────────────────────────────────────────────
    def _step_summary(self, task: AgentTask) -> str:
        parts = []
        for s in task.steps:
            if s.status == StepStatus.SUCCESS:
                parts.append(f"✓ {s.description}: {s.result}")
            elif s.status == StepStatus.FAILED:
                parts.append(f"✗ {s.description}: {s.error}")
        return "\n".join(parts)

    def _compile_result(self, task: AgentTask, user_text: str) -> str:
        """Generate a clean, human-like response for quick-match actions."""
        all_ok = all(s.status == StepStatus.SUCCESS for s in task.steps)

        if all_ok and task.steps:
            step = task.steps[0]
            tool = step.tool
            result_msg = step.result or ""

            if tool == "open_app":
                name = step.params.get("name", "app")
                return f"Done! {name.title()} is now open."
            elif tool == "app_control":
                action = step.params.get("action", "")
                target = step.params.get("target", "window")
                if action == "close":
                    return f"Done, closed {target}."
                elif action == "focus":
                    return f"Switched to {target}."
                return result_msg or "Done!"
            elif tool == "organize_files":
                return f"Files organized!\n{result_msg}"
            elif tool == "desktop_action":
                action = step.params.get("action", "")
                if action == "list_windows":
                    return f"Here are the open windows:\n{result_msg}"
                elif action == "list_files":
                    return f"Here are the files:\n{result_msg}"
                return result_msg or "Done!"
            elif tool == "screen_analyze":
                return f"Here's what's on screen:\n{result_msg}"
            elif tool == "keyboard_type":
                return "Typed it!"
            elif tool == "system_info":
                return f"System info:\n{result_msg}"
            else:
                return result_msg or "Done!"

        elif not all_ok and task.steps:
            failed = [s for s in task.steps if s.status == StepStatus.FAILED]
            if failed:
                err = failed[0].error or "unknown error"
                return f"Sorry, that didn't work: {err}"

        return self._step_summary(task) or "Done!"

    # ── Tool extraction ─────────────────────────────────────────────────
    def _extract_tool_calls(self, response: str) -> list:
        pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        matches = re.findall(pattern, response, re.DOTALL)
        calls = []
        for match in matches:
            try:
                data = json.loads(match)
                if "tool" in data:
                    calls.append(data)
            except json.JSONDecodeError:
                pass
        if not calls:
            bare = re.findall(r'\{[^{}]*"tool"[^{}]*\}', response, re.DOTALL)
            for match in bare:
                try:
                    data = json.loads(match)
                    if "tool" in data:
                        calls.append(data)
                except Exception:
                    pass
        return calls

    def _strip_tool_blocks(self, text: str) -> str:
        text = re.sub(r"```(?:json)?\s*\{.*?\}\s*```", "", text, flags=re.DOTALL)
        text = re.sub(r'\{[^{}]*"tool"[^{}]*\}', "", text, flags=re.DOTALL)
        return text.strip()

    def _emit_thinking(self, text: str):
        if self._on_thinking:
            self._on_thinking(text)

    @property
    def is_running(self) -> bool:
        return self._running


# ═══════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT — Clear English, intelligent, step-by-step
# ═══════════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """You are Aura-X, an intelligent and powerful AI desktop assistant built by Prateek.

## Your Personality
- You are warm, helpful, and confident.
- You speak in clear, natural English. Keep responses concise — 2-3 sentences for simple queries, more for complex ones.
- You are loyal, protective, and never do anything destructive without asking first.
- Think step-by-step before answering complex questions.
- Be conversational and human-like, not robotic.

## Tools — Use these to perform actions
When you need to DO something on the computer, output a JSON block with the tool call.

### Apps & Windows
- **open_app**: `{"tool": "open_app", "params": {"name": "chrome"}, "explanation": "Opening Chrome"}`
- **app_control**: Control windows:
  - Focus: `{"tool": "app_control", "params": {"action": "focus", "target": "Chrome"}, "explanation": "Switching to Chrome"}`
  - Close: `{"tool": "app_control", "params": {"action": "close", "target": "Notepad"}, "explanation": "Closing Notepad"}`
  - Inspect: `{"tool": "app_control", "params": {"action": "inspect"}, "explanation": "Reading active window"}`
  - Click: `{"tool": "app_control", "params": {"action": "click_element", "text": "Save"}, "explanation": "Clicking Save"}`
  - Type: `{"tool": "app_control", "params": {"action": "type_in", "target": "Notepad", "text": "Hello"}, "explanation": "Typing into Notepad"}`
- **desktop_action**: `{"action": "list_windows"}`, `{"action": "close_app", "name": "chrome"}`, `{"action": "list_files", "path": "..."}`

### File Operations
- **file_operation**: Copy, move, rename, find, read, write, stats, delete files.
  - Example: `{"tool": "file_operation", "params": {"action": "find", "path": "C:/Users/heman/Desktop", "pattern": "report"}, "explanation": "Finding files"}`
- **organize_files**: `{"tool": "organize_files", "params": {"path": "...", "mode": "smart"}, "explanation": "Organizing files"}`
- **write_code**: `{"tool": "write_code", "params": {"filepath": "...", "content": "..."}, "explanation": "Saving code"}`

### Input & Screen
- **keyboard_type**: `{"params": {"text": "hello"}}` or `{"params": {"key": "enter"}}` or `{"params": {"hotkey": ["ctrl", "c"]}}`
- **mouse_click**: `{"params": {"x": 500, "y": 300}}` or `{"params": {"target_text": "OK"}}`
- **screen_analyze**: `{"params": {"mode": "full"}}` or `{"params": {"mode": "find", "target_text": "Save"}}`

### Office & Web
- **create_word_doc**: `{"params": {"filepath": "report.docx", "title": "Report", "content": "..."}}`
- **create_excel_sheet**: `{"params": {"filepath": "data.xlsx", "headers": ["Name","Age"], "data": [["A",25]]}}`
- **create_ppt**: `{"params": {"filepath": "pres.pptx", "title": "Talk", "slides": [{"title": "Slide 1", "content": "..."}]}}`
- **web_scrape**: `{"params": {"url": "...", "action": "summary"}}`
- **run_command**: `{"params": {"command": "dir C:/Users/heman/Desktop"}}`
- **system_info**: `{"params": {"type": "general"}}`

## CRITICAL RULES
1. When user says "open X" → use the open_app tool. "close X" → use app_control.
2. For file tasks (find, move, copy, rename, delete) → use file_operation or organize_files. Actually DO it, don't just describe it.
3. ALWAYS output a tool call JSON block when the user asks you to perform an action.
4. Ask permission before deleting files or running risky commands.
5. Always respond in English only.
6. Address the user naturally — "Boss" or by name "Prateek" occasionally."""
