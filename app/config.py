from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _parse_roots(name: str, default: str) -> tuple[Path, ...]:
    raw = os.getenv(name, default)
    roots: list[Path] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        roots.append(Path(item).expanduser().resolve())
    if not roots:
        raise RuntimeError(f"{name} must contain at least one path")
    return tuple(roots)


@dataclass(frozen=True)
class Settings:
    input_roots: tuple[Path, ...] = _parse_roots("VCSI_INPUT_ROOTS", "/media")
    output_roots: tuple[Path, ...] = _parse_roots("VCSI_OUTPUT_ROOTS", "/output")
    vcsi_binary: str = os.getenv("VCSI_BINARY", "vcsi")
    max_log_lines: int = int(os.getenv("VCSI_MAX_LOG_LINES", "1000"))


settings = Settings()
