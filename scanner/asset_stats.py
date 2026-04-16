from __future__ import annotations

from pathlib import Path


SKIP_DIRS = {"Library", "Temp", "Packages", "obj", ".git"}
TEXTURE_EXTS = {".png", ".jpg", ".jpeg", ".tga", ".psd", ".bmp"}


def _iter_files(project_root: Path, relative_path: str):
    base = (project_root / relative_path).resolve()
    if not base.exists():
        return

    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def scan_asset_sizes(project_path: str, relative_path: str = "Assets") -> dict:
    project_root = Path(project_path).resolve()
    stats: dict[str, dict[str, float]] = {}
    total_files = 0
    total_size = 0

    for file_path in _iter_files(project_root, relative_path) or []:
        ext = file_path.suffix.lower() or "[no_ext]"
        entry = stats.setdefault(ext, {"count": 0, "size_bytes": 0})
        size_bytes = file_path.stat().st_size
        entry["count"] += 1
        entry["size_bytes"] += size_bytes
        total_files += 1
        total_size += size_bytes

    by_extension = [
        {
            "extension": ext,
            "count": int(data["count"]),
            "size_bytes": int(data["size_bytes"]),
            "size_mb": round(data["size_bytes"] / (1024 * 1024), 3),
        }
        for ext, data in sorted(stats.items(), key=lambda item: item[1]["size_bytes"], reverse=True)
    ]

    return {
        "root": relative_path,
        "total_files": total_files,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 3),
        "by_extension": by_extension,
    }


def scan_texture_info(project_path: str, relative_path: str = "Assets", limit: int = 50) -> dict:
    project_root = Path(project_path).resolve()
    items = []

    for file_path in _iter_files(project_root, relative_path) or []:
        if file_path.suffix.lower() not in TEXTURE_EXTS:
            continue

        size_bytes = file_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        level = "ok"
        if size_mb > 4:
            level = "oversized"
        elif size_mb > 1:
            level = "large"

        items.append(
            {
                "path": str(file_path.relative_to(project_root)).replace("\\", "/"),
                "size_bytes": size_bytes,
                "size_mb": round(size_mb, 3),
                "level": level,
            }
        )
        if len(items) >= limit:
            break

    return {
        "root": relative_path,
        "count": len(items),
        "textures": items,
    }
