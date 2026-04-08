import subprocess
import platform
import shlex
from typing import Dict
from core.config import CONFIG
from core.logger import setup_logger

logger = setup_logger("aura_x.tools.command")

SAFE_COMMANDS = CONFIG.get("safe_commands", [])
BLOCKED_COMMANDS = CONFIG.get("blocked_commands", [])
PLATFORM = platform.system()


def _is_blocked(command: str) -> bool:
    cmd_lower = command.lower().strip()
    for blocked in BLOCKED_COMMANDS:
        if blocked.lower() in cmd_lower:
            return True
    return False


def handle_run_command(params: Dict) -> Dict:
    command = params.get("command", "").strip()
    if not command:
        return {"status": "error", "error": "No command specified"}

    if _is_blocked(command):
        return {"status": "error", "error": f"Command blocked for safety: {command}"}

    timeout = params.get("timeout", 30)
    working_dir = params.get("cwd") or None
    capture = params.get("capture", True)

    try:
        if PLATFORM == "Windows":
            result = subprocess.run(
                command,
                shell=True,
                capture_output=capture,
                text=True,
                timeout=timeout,
                cwd=working_dir
            )
        else:
            args = shlex.split(command)
            result = subprocess.run(
                args,
                capture_output=capture,
                text=True,
                timeout=timeout,
                cwd=working_dir
            )

        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""
        returncode = result.returncode

        if returncode == 0:
            output = stdout or "(No output)"
            return {
                "status": "success",
                "message": f"Command completed. Output:\n{output[:2000]}",
                "stdout": stdout,
                "stderr": stderr,
                "returncode": returncode
            }
        else:
            return {
                "status": "error",
                "error": f"Command failed (exit {returncode}): {stderr or stdout}",
                "stdout": stdout,
                "stderr": stderr,
                "returncode": returncode
            }

    except subprocess.TimeoutExpired:
        return {"status": "error", "error": f"Command timed out after {timeout}s"}
    except FileNotFoundError:
        return {"status": "error", "error": f"Command not found: {command.split()[0]}"}
    except Exception as e:
        logger.error(f"Command execution error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
