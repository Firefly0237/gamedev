from __future__ import annotations

import os
import platform
from pathlib import Path

from config.settings import Settings


WINDOWS_CANDIDATES = [
    "C:/Program Files/Unity/Hub/Editor",
    "C:/Program Files/Unity/Editor",
]
MACOS_CANDIDATES = ["/Applications/Unity/Hub/Editor"]
LINUX_CANDIDATES = ["~/Unity/Hub/Editor", "/opt/unity/Editor"]


def _candidate_roots() -> list[Path]:
    system = platform.system()
    raw = []
    if system == "Windows":
        raw = WINDOWS_CANDIDATES
    elif system == "Darwin":
        raw = MACOS_CANDIDATES
    else:
        raw = LINUX_CANDIDATES
    return [Path(path).expanduser() for path in raw]


def detect_unity_installations() -> list[str]:
    candidates: list[str] = []

    if Settings.UNITY_EXECUTABLE_PATH and os.path.isfile(Settings.UNITY_EXECUTABLE_PATH):
        candidates.append(Settings.UNITY_EXECUTABLE_PATH)

    for root in _candidate_roots():
        if not root.exists():
            continue
        for version_dir in sorted(root.iterdir(), reverse=True):
            if platform.system() == "Windows":
                executable = version_dir / "Editor" / "Unity.exe"
            elif platform.system() == "Darwin":
                executable = version_dir / "Unity.app" / "Contents" / "MacOS" / "Unity"
            else:
                executable = version_dir / "Editor" / "Unity"

            if executable.exists():
                path = str(executable)
                if path not in candidates:
                    candidates.append(path)

    return candidates


def get_preferred_unity_path() -> str:
    installs = detect_unity_installations()
    return installs[0] if installs else ""
