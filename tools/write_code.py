"""
Aura-X — Write / Save Code Files
"""

import os
from pathlib import Path
from typing import Dict
from core.logger import setup_logger

logger = setup_logger("aura_x.tools.write_code")


def handle_write_code(params: Dict) -> Dict:
    """Create or save a code file. Accepts 'filepath' (direct) or 'filename'+'directory'."""
    content = params.get("content", "")
    if not content:
        return {"status": "error", "error": "No code content provided"}

    # Support direct filepath (what the LLM sends) or filename+directory
    filepath = params.get("filepath", "")
    if filepath:
        filepath = Path(filepath)
    else:
        filename = params.get("filename", "")
        language = params.get("language", "python")
        directory = params.get("directory", str(Path.home() / "AuraXCode"))

        if not filename:
            ext_map = {
                "python": ".py", "javascript": ".js", "typescript": ".ts",
                "java": ".java", "cpp": ".cpp", "c": ".c", "html": ".html",
                "css": ".css", "bash": ".sh", "powershell": ".ps1",
                "sql": ".sql", "go": ".go", "rust": ".rs", "ruby": ".rb",
            }
            ext = ext_map.get(language.lower(), ".txt")
            filename = f"generated_code{ext}"

        filepath = Path(directory) / filename

    try:
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Handle collision
        if filepath.exists():
            stem = filepath.stem
            suffix = filepath.suffix
            counter = 1
            while filepath.exists():
                filepath = filepath.parent / f"{stem}_{counter}{suffix}"
                counter += 1

        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Code written to: {filepath}")
        return {
            "status": "success",
            "message": f"Code saved to {filepath}",
            "path": str(filepath),
            "lines": len(content.splitlines())
        }
    except Exception as e:
        logger.error(f"Write code error: {e}")
        return {"status": "error", "error": str(e)}
