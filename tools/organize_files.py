"""
Aura-X Smart File Organizer
AI-powered file organization with real-world intelligence:
- Content/name analysis (invoices, screenshots, projects)
- Date-based grouping (today, this week, this month, older)
- Project detection (groups related files together)
- Duplicate detection
- Size-aware categorization
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from core.config import CONFIG
from core.logger import setup_logger

logger = setup_logger("aura_x.tools.organize")

ORGANIZE_RULES = CONFIG.get("organize_rules", {})


# ─── Smart Name Patterns ─────────────────────────────────────
NAME_PATTERNS = {
    "screenshots": [
        r"screenshot", r"screen.?shot", r"capture", r"snip", r"clip",
        r"Screen Shot", r"Screenclip", r"IMG_\d{4}", r"Screenshot_\d+",
        r"Screen Recording"
    ],
    "downloads": [
        r"download", r"^dl_", r"installer", r"setup",
        r"^Unconfirmed", r"\.crdownload$", r"\.part$"
    ],
    "documents_work": [
        r"invoice", r"receipt", r"bill", r"payment", r"statement",
        r"report", r"proposal", r"contract", r"agreement", r"resume",
        r"cv[\s_-]", r"cover.?letter", r"memo", r"minutes", r"agenda",
        r"budget", r"expense", r"tax", r"form[\s_-]", r"application"
    ],
    "documents_personal": [
        r"diary", r"journal", r"note[\s_-]", r"todo", r"list",
        r"recipe", r"letter[\s_-]", r"medical", r"health",
        r"insurance", r"warranty", r"manual"
    ],
    "school_academic": [
        r"assignment", r"homework", r"hw[\s_-]?\d", r"thesis",
        r"dissertation", r"essay", r"lab.?report", r"lecture",
        r"syllabus", r"exam", r"quiz", r"study", r"chapter",
        r"semester", r"course", r"class[\s_-]"
    ],
    "projects": [
        r"project", r"v\d+\.\d+", r"draft", r"final",
        r"backup", r"old[\s_-]", r"new[\s_-]", r"copy[\s_-]"
    ],
    "temp_junk": [
        r"^~\$", r"\.tmp$", r"\.bak$", r"^Thumbs\.db$",
        r"^desktop\.ini$", r"^\.DS_Store$", r"^\._",
        r"^temp[\s_-]", r"^untitled"
    ]
}

# Common project indicators (files that suggest a project directory)
PROJECT_INDICATORS = {
    "python": [".py", "requirements.txt", "setup.py", "pyproject.toml", "__init__.py"],
    "node": ["package.json", "node_modules", ".npmrc"],
    "web": ["index.html", "style.css", "app.js"],
    "git": [".git", ".gitignore"],
    "java": ["pom.xml", "build.gradle", ".java"],
    "dotnet": [".csproj", ".sln"],
}


def _match_name_pattern(filename: str) -> Optional[str]:
    """Match filename against smart patterns."""
    name_lower = filename.lower()
    for category, patterns in NAME_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, name_lower, re.IGNORECASE):
                return category
    return None


def _classify_by_content_hints(filepath: Path) -> Optional[str]:
    """Try to classify by peeking at file content for common patterns."""
    ext = filepath.suffix.lower()

    # Only peek at text-like files
    text_exts = {".txt", ".md", ".csv", ".json", ".xml", ".log", ".html", ".htm"}
    if ext not in text_exts:
        return None

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(1000).lower()

        # Invoice/receipt detection
        invoice_keywords = ["invoice", "receipt", "total amount", "payment due", "bill to", "subtotal"]
        if sum(1 for kw in invoice_keywords if kw in head) >= 2:
            return "documents_financial"

        # Code detection for .txt files
        code_patterns = ["import ", "def ", "class ", "function ", "var ", "const ", "#include"]
        if sum(1 for p in code_patterns if p in head) >= 2:
            return "code"

        # Log file detection
        log_patterns = ["error", "warning", "info", "debug", "traceback", "exception"]
        if sum(1 for p in log_patterns if p in head) >= 3:
            return "logs"

    except Exception:
        pass

    return None


def _get_date_bucket(mod_time: datetime) -> str:
    """Categorize file by modification date."""
    now = datetime.now()
    delta = now - mod_time

    if delta.days == 0:
        return "Today"
    elif delta.days <= 7:
        return "This Week"
    elif delta.days <= 30:
        return "This Month"
    elif delta.days <= 90:
        return "Last 3 Months"
    elif delta.days <= 365:
        return "This Year"
    else:
        return f"{mod_time.year}"


def _detect_file_groups(files: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Detect related file groups based on naming patterns.
    Groups files that share a common base name (e.g., report.docx, report_v2.docx, report_final.docx).
    """
    groups = defaultdict(list)

    for f in files:
        stem = f["stem"].lower()
        # Strip version/copy suffixes to find the base name
        base = re.sub(r'[\s_-]*(v\d+|final|draft|copy|old|new|backup|\(\d+\))[\s_-]*', '', stem)
        base = re.sub(r'[\s_-]+\d{4,}$', '', base)  # Strip trailing timestamps
        base = re.sub(r'[\s_-]+$', '', base)

        if len(base) > 2:
            groups[base].append(f)

    # Only return groups with multiple files
    return {k: v for k, v in groups.items() if len(v) > 1}


def _estimate_importance(file_info: Dict) -> float:
    """Estimate file importance for organization priority."""
    score = 0.5
    size = file_info.get("size", 0)

    # Larger files are more important
    if size > 10 * 1024 * 1024:  # > 10MB
        score += 0.2
    elif size > 1024 * 1024:  # > 1MB
        score += 0.1

    # Recently modified files are more important
    try:
        mod = datetime.fromisoformat(file_info.get("modified", ""))
        if (datetime.now() - mod).days < 7:
            score += 0.2
        elif (datetime.now() - mod).days < 30:
            score += 0.1
    except Exception:
        pass

    # Work documents are important
    if file_info.get("smart_category") in ("documents_work", "documents_financial", "school_academic"):
        score += 0.15

    return min(score, 1.0)


def smart_classify_file(filepath: Path) -> Dict:
    """
    Intelligently classify a file using multiple signals:
    1. Extension-based category
    2. Name pattern matching
    3. Content hints
    4. Date bucketing
    """
    ext = filepath.suffix.lower()
    stat = filepath.stat()
    mod_time = datetime.fromtimestamp(stat.st_mtime)

    result = {
        "path": str(filepath),
        "name": filepath.name,
        "stem": filepath.stem,
        "extension": ext,
        "size": stat.st_size,
        "modified": mod_time.isoformat(),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
    }

    # 1. Extension-based category
    ext_category = None
    for category, extensions in ORGANIZE_RULES.items():
        if ext in extensions:
            ext_category = category
            break

    # 2. Smart name pattern matching
    name_category = _match_name_pattern(filepath.name)

    # 3. Content hints
    content_category = _classify_by_content_hints(filepath)

    # 4. Date bucket
    result["date_bucket"] = _get_date_bucket(mod_time)

    # Priority: content hints > name patterns > extension
    if content_category:
        result["smart_category"] = content_category
        result["category_source"] = "content"
    elif name_category:
        result["smart_category"] = name_category
        result["category_source"] = "name_pattern"
    elif ext_category:
        result["smart_category"] = ext_category
        result["category_source"] = "extension"
    else:
        result["smart_category"] = "misc"
        result["category_source"] = "default"

    # Check for temp/junk
    if name_category == "temp_junk":
        result["smart_category"] = "temp_junk"
        result["category_source"] = "name_pattern"

    result["importance"] = _estimate_importance(result)

    return result


def handle_organize_files(params: Dict) -> Dict:
    """
    Smart file organization with real-world intelligence.

    Params:
        path: Directory to organize
        mode: 'smart' (AI-powered) | 'extension' (simple) | 'date' (by date) | 'analyze' (dry run report)
        target: Target directory (defaults to same as source)
        recursive: Whether to scan subdirectories
    """
    source_path = params.get("path", "").strip()
    if not source_path:
        return {"status": "error", "error": "No path specified"}

    source = Path(source_path)
    if not source.exists():
        return {"status": "error", "error": f"Path does not exist: {source_path}"}

    mode = params.get("mode", "smart").lower()
    target = Path(params.get("target", str(source)))
    recursive = params.get("recursive", False)
    dry_run = params.get("dry_run", False) or mode == "analyze"

    # Scan files
    try:
        pattern = "**/*" if recursive else "*"
        files = []
        for item in source.glob(pattern):
            if item.is_file() and not item.name.startswith("."):
                try:
                    classified = smart_classify_file(item)
                    files.append(classified)
                except PermissionError:
                    logger.warning(f"Permission denied: {item}")
                except Exception as e:
                    logger.debug(f"File classify error {item}: {e}")
    except Exception as e:
        return {"status": "error", "error": f"Scan error: {e}"}

    if not files:
        return {"status": "success", "message": f"No files found in {source_path}"}

    # Detect related file groups
    groups = _detect_file_groups(files)

    # ─── Analysis mode: just report what would happen ───
    if mode == "analyze":
        return _generate_analysis(files, groups, source_path)

    # ─── Smart organization ───
    operations = []
    stats = {"total": len(files), "moved": 0, "skipped": 0, "errors": 0, "by_category": {}}

    # Map categories to folder names
    FOLDER_MAP = {
        "images": "📸 Images",
        "screenshots": "📸 Screenshots",
        "documents": "📄 Documents",
        "documents_work": "📄 Documents/Work",
        "documents_personal": "📄 Documents/Personal",
        "documents_financial": "📄 Documents/Financial",
        "school_academic": "🎓 Academic",
        "videos": "🎬 Videos",
        "audio": "🎵 Audio",
        "code": "💻 Code",
        "archives": "📦 Archives",
        "spreadsheets": "📊 Spreadsheets",
        "presentations": "📎 Presentations",
        "executables": "⚙ Programs",
        "downloads": "⬇ Downloads",
        "projects": "🗂 Projects",
        "logs": "📋 Logs",
        "temp_junk": "🗑 Temp",
        "misc": "📁 Other",
    }

    if mode == "date":
        # Organize by date buckets
        for f in files:
            file_path = Path(f["path"])
            date_folder = f.get("date_bucket", "Other")
            dest_dir = target / date_folder
            dest_file = dest_dir / file_path.name

            if file_path.parent == dest_dir:
                stats["skipped"] += 1
                continue

            if dest_file.exists():
                dest_file = _unique_name(dest_file)

            operations.append({"src": str(file_path), "dst": str(dest_file), "category": date_folder})

            if not dry_run:
                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(dest_file))
                    stats["moved"] += 1
                    stats["by_category"][date_folder] = stats["by_category"].get(date_folder, 0) + 1
                except Exception as e:
                    stats["errors"] += 1
                    logger.error(f"Move error: {e}")

    else:
        # Smart mode: use intelligent classification
        # First, handle grouped files (keep them together)
        grouped_files = set()
        for group_name, group_files in groups.items():
            if len(group_files) >= 2:
                # Determine the dominant category for the group
                categories = [f["smart_category"] for f in group_files]
                dominant = max(set(categories), key=categories.count)
                folder = FOLDER_MAP.get(dominant, f"📁 {dominant.replace('_', ' ').title()}")

                for f in group_files:
                    file_path = Path(f["path"])
                    grouped_files.add(f["path"])
                    dest_dir = target / folder
                    dest_file = dest_dir / file_path.name

                    if file_path.parent == dest_dir:
                        stats["skipped"] += 1
                        continue

                    if dest_file.exists():
                        dest_file = _unique_name(dest_file)

                    operations.append({"src": str(file_path), "dst": str(dest_file),
                                       "category": folder, "group": group_name})

                    if not dry_run:
                        try:
                            dest_dir.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(file_path), str(dest_file))
                            stats["moved"] += 1
                            stats["by_category"][folder] = stats["by_category"].get(folder, 0) + 1
                        except Exception as e:
                            stats["errors"] += 1

        # Then handle remaining ungrouped files
        for f in files:
            if f["path"] in grouped_files:
                continue

            file_path = Path(f["path"])
            category = f["smart_category"]
            folder = FOLDER_MAP.get(category, f"📁 {category.replace('_', ' ').title()}")
            dest_dir = target / folder
            dest_file = dest_dir / file_path.name

            if file_path.parent == dest_dir:
                stats["skipped"] += 1
                continue

            if dest_file.exists():
                dest_file = _unique_name(dest_file)

            operations.append({"src": str(file_path), "dst": str(dest_file), "category": folder})

            if not dry_run:
                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(dest_file))
                    stats["moved"] += 1
                    stats["by_category"][folder] = stats["by_category"].get(folder, 0) + 1
                except Exception as e:
                    stats["errors"] += 1
                    logger.error(f"Move error: {e}")

    # Build summary
    summary_parts = [f"{count} → {cat}" for cat, count in sorted(stats["by_category"].items())]
    action = "Would move" if dry_run else "Organized"
    summary = f"{action} {stats['moved']}/{stats['total']} files:\n" + "\n".join(summary_parts)
    if stats["errors"]:
        summary += f"\n⚠ {stats['errors']} errors"
    if groups:
        summary += f"\n📎 {len(groups)} related file groups detected"

    # Open the target folder in Explorer to show results
    if not dry_run and stats["moved"] > 0:
        try:
            import subprocess
            subprocess.Popen(["explorer", str(target)])
            summary += f"\n\n📂 Opened folder in Explorer"
        except Exception:
            pass

    return {
        "status": "success",
        "message": summary,
        "stats": stats,
        "groups_detected": len(groups),
        "operations": operations if dry_run else [],
        "target_path": str(target)
    }


def _generate_analysis(files: List[Dict], groups: Dict, source_path: str) -> Dict:
    """Generate a detailed analysis report without moving anything."""
    by_category = defaultdict(list)
    for f in files:
        by_category[f["smart_category"]].append(f)

    total_size = sum(f["size"] for f in files)

    report_lines = [
        f"📊 File Analysis: {source_path}",
        f"   Total: {len(files)} files ({_human_size(total_size)})",
        ""
    ]

    for cat, cat_files in sorted(by_category.items()):
        cat_size = sum(f["size"] for f in cat_files)
        sources = defaultdict(int)
        for f in cat_files:
            sources[f.get("category_source", "unknown")] += 1
        source_info = ", ".join(f"{s}:{c}" for s, c in sources.items())
        report_lines.append(
            f"   {cat}: {len(cat_files)} files ({_human_size(cat_size)}) [{source_info}]"
        )

    if groups:
        report_lines.append(f"\n📎 Related File Groups ({len(groups)}):")
        for name, gfiles in list(groups.items())[:10]:
            names = ", ".join(f["name"] for f in gfiles[:3])
            if len(gfiles) > 3:
                names += f" +{len(gfiles)-3} more"
            report_lines.append(f"   • {name}: {names}")

    # Find duplicates by size
    size_groups = defaultdict(list)
    for f in files:
        if f["size"] > 1024:  # Skip tiny files
            size_groups[f["size"]].append(f)
    potential_dupes = {s: fs for s, fs in size_groups.items() if len(fs) > 1}
    if potential_dupes:
        report_lines.append(f"\n⚠ Potential Duplicates ({len(potential_dupes)} groups):")
        for size, dupes in list(potential_dupes.items())[:5]:
            names = ", ".join(d["name"] for d in dupes)
            report_lines.append(f"   • {_human_size(size)}: {names}")

    return {
        "status": "success",
        "message": "\n".join(report_lines),
        "file_count": len(files),
        "categories": {k: len(v) for k, v in by_category.items()},
        "groups": len(groups),
        "potential_duplicates": len(potential_dupes)
    }


def _unique_name(filepath: Path) -> Path:
    """Generate a unique filename to avoid overwrite."""
    stem = filepath.stem
    suffix = filepath.suffix
    parent = filepath.parent
    counter = 1
    while filepath.exists():
        filepath = parent / f"{stem}_{counter}{suffix}"
        counter += 1
    return filepath


def _human_size(size_bytes: int) -> str:
    size_val = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_val < 1024:
            return f"{size_val:.1f} {unit}"
        size_val /= 1024
    return f"{size_val:.1f} PB"
