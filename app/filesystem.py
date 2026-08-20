from __future__ import annotations

from pathlib import Path
from typing import Iterable

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".m4v", ".webm", ".wmv", ".flv",
    ".mpeg", ".mpg", ".ts", ".m2ts", ".mts", ".vob", ".3gp", ".ogv",
}


def is_within(path: Path, roots: Iterable[Path]) -> bool:
    resolved = path.resolve()
    for root in roots:
        root = root.resolve()
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            pass
    return False


def resolve_allowed(raw_path: str, roots: tuple[Path, ...], *, must_exist: bool = True) -> Path:
    path = Path(raw_path).expanduser().resolve()
    if not is_within(path, roots):
        raise ValueError("Path is outside configured roots")
    if must_exist and not path.exists():
        raise ValueError("Path does not exist")
    return path


def default_root(roots: tuple[Path, ...]) -> Path:
    return roots[0]


def browse(path: Path, roots: tuple[Path, ...], *, videos_only: bool) -> dict:
    if not path.is_dir():
        raise ValueError("Path is not a directory")

    entries = []
    try:
        children = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError as exc:
        raise ValueError("Permission denied") from exc

    for child in children:
        try:
            stat = child.stat()
        except OSError:
            continue

        if child.is_dir():
            entries.append({
                "name": child.name,
                "path": str(child),
                "type": "directory",
                "size": None,
                "modified": int(stat.st_mtime),
            })
        elif not videos_only or child.suffix.lower() in VIDEO_EXTENSIONS:
            entries.append({
                "name": child.name,
                "path": str(child),
                "type": "file",
                "size": stat.st_size,
                "modified": int(stat.st_mtime),
            })

    parent = path.parent if is_within(path.parent, roots) else None
    return {
        "current": str(path),
        "parent": str(parent) if parent else None,
        "roots": [str(root) for root in roots],
        "entries": entries,
    }
