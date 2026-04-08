import os
import shutil
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from core.config import CONFIG
from core.logger import setup_logger

logger = setup_logger("aura_x.automation.filesystem")

ORGANIZE_RULES = CONFIG.get("organize_rules", {})


def classify_file(filepath: Path) -> str:
    """Classify a file by extension and naming heuristics."""
    ext = filepath.suffix.lower()
    name = filepath.stem.lower()

    for category, extensions in ORGANIZE_RULES.items():
        if ext in extensions:
            return category

    # MIME type fallback
    mime, _ = mimetypes.guess_type(str(filepath))
    if mime:
        if mime.startswith("image/"):
            return "images"
        elif mime.startswith("video/"):
            return "videos"
        elif mime.startswith("audio/"):
            return "audio"
        elif mime.startswith("text/"):
            return "documents"
        elif "pdf" in mime:
            return "documents"

    # Name heuristics
    if any(kw in name for kw in ["screenshot", "screen", "capture", "snap"]):
        return "images"
    if any(kw in name for kw in ["download", "installer", "setup", "install"]):
        return "executables"
    if any(kw in name for kw in ["backup", "bak", "archive"]):
        return "archives"
    if any(kw in name for kw in ["invoice", "receipt", "bill", "payment"]):
        return "documents"

    return "misc"


def scan_directory(path: str, recursive: bool = True) -> List[Dict]:
    results = []
    root_path = Path(path)

    if not root_path.exists():
        logger.error(f"Path does not exist: {path}")
        return results

    try:
        pattern = "**/*" if recursive else "*"
        for item in root_path.glob(pattern):
            if item.is_file():
                try:
                    stat = item.stat()
                    results.append({
                        "path": str(item),
                        "name": item.name,
                        "stem": item.stem,
                        "extension": item.suffix.lower(),
                        "size": stat.st_size,
                        "size_human": _human_size(stat.st_size),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "category": classify_file(item),
                        "parent": str(item.parent)
                    })
                except PermissionError:
                    logger.warning(f"Permission denied: {item}")
                except Exception as e:
                    logger.debug(f"File stat error {item}: {e}")
    except Exception as e:
        logger.error(f"Directory scan error: {e}")

    return results


def organize_directory(
    source_path: str,
    target_path: Optional[str] = None,
    dry_run: bool = False,
    recursive: bool = False
) -> Dict:
    source = Path(source_path)
    target = Path(target_path) if target_path else source

    if not source.exists():
        return {"status": "error", "message": f"Source path does not exist: {source_path}"}

    files = scan_directory(source_path, recursive=recursive)
    stats = {"total": len(files), "moved": 0, "skipped": 0, "errors": 0, "by_category": {}}
    operations = []

    for file_info in files:
        file_path = Path(file_info["path"])
        category = file_info["category"]
        dest_dir = target / category

        if file_path.parent == dest_dir:
            stats["skipped"] += 1
            continue
        if file_path.name.startswith("."):
            stats["skipped"] += 1
            continue

        dest_file = dest_dir / file_path.name

        if dest_file.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            counter = 1
            while dest_file.exists():
                dest_file = dest_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        operations.append({"src": str(file_path), "dst": str(dest_file), "category": category})

        if not dry_run:
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(dest_file))
                stats["moved"] += 1
                stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
            except Exception as e:
                stats["errors"] += 1
                logger.error(f"Move error {file_path}: {e}")
        else:
            stats["moved"] += 1
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

    summary_parts = [f"{count} {cat}" for cat, count in stats["by_category"].items()]
    summary = f"{'Would move' if dry_run else 'Moved'} {stats['moved']} files: " + ", ".join(summary_parts)
    if stats["errors"]:
        summary += f" ({stats['errors']} errors)"

    return {
        "status": "success",
        "message": summary,
        "stats": stats,
        "operations": operations if dry_run else []
    }


def create_directory(path: str) -> Dict:
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return {"status": "success", "message": f"Directory created: {path}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def delete_file_or_dir(path: str, safe: bool = True) -> Dict:
    target = Path(path)
    if not target.exists():
        return {"status": "error", "error": f"Path not found: {path}"}
    try:
        if safe:
            trash_dir = Path.home() / ".aura_x_trash"
            trash_dir.mkdir(exist_ok=True)
            dest = trash_dir / f"{target.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.move(str(target), str(dest))
            return {"status": "success", "message": f"Moved to trash: {target.name}"}
        else:
            if target.is_file():
                target.unlink()
            else:
                shutil.rmtree(str(target))
            return {"status": "success", "message": f"Deleted: {path}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def copy_file(src: str, dst: str) -> Dict:
    try:
        src_path, dst_path = Path(src), Path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        if src_path.is_file():
            shutil.copy2(str(src_path), str(dst_path))
        else:
            shutil.copytree(str(src_path), str(dst_path))
        return {"status": "success", "message": f"Copied: {src} → {dst}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def rename_file(src: str, new_name: str) -> Dict:
    try:
        src_path = Path(src)
        new_path = src_path.parent / new_name
        src_path.rename(new_path)
        return {"status": "success", "message": f"Renamed to: {new_name}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_directory_stats(path: str) -> Dict:
    try:
        p = Path(path)
        if not p.exists():
            return {"status": "error", "error": "Path not found"}
        total_size = file_count = dir_count = 0
        by_category: dict = {}
        for item in p.rglob("*"):
            if item.is_file():
                try:
                    total_size += item.stat().st_size
                    file_count += 1
                    cat = classify_file(item)
                    by_category[cat] = by_category.get(cat, 0) + 1
                except Exception:
                    pass
            elif item.is_dir():
                dir_count += 1
        return {
            "status": "success",
            "path": path,
            "total_size": _human_size(total_size),
            "file_count": file_count,
            "dir_count": dir_count,
            "by_category": by_category
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def find_files(
    path: str,
    pattern: str = "*",
    category: Optional[str] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None
) -> List[Dict]:
    files = scan_directory(path, recursive=True)
    results = []
    for f in files:
        if pattern != "*" and pattern.lower() not in f["name"].lower():
            continue
        if category and f["category"] != category:
            continue
        if min_size and f["size"] < min_size:
            continue
        if max_size and f["size"] > max_size:
            continue
        results.append(f)
    return results


def read_text_file(path: str, encoding: str = "utf-8") -> Dict:
    try:
        content = Path(path).read_text(encoding=encoding, errors="replace")
        return {"status": "success", "content": content, "path": path}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def write_text_file(path: str, content: str, encoding: str = "utf-8", append: bool = False) -> Dict:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(str(p), mode, encoding=encoding) as f:
            f.write(content)
        return {"status": "success", "message": f"Written to {path}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _human_size(size_bytes: int) -> str:
    size_value = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_value < 1024:
            return f"{size_value:.1f} {unit}"
        size_value /= 1024
    return f"{size_value:.1f} PB"
