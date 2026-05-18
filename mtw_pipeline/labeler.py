from __future__ import annotations

import csv
from pathlib import Path

from .models import ClipRecord, LabelValue


VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".mts", ".m2ts"}
MULTI_LABEL_FIELDS = {"context", "emotion", "subject", "marketing_use", "platform", "quality"}
META_FIELDS = {"filename", "trim_start", "trim_end", "notes"}


def load_clip_labels(csv_path: str | Path, clips_dir: str | Path = "clips") -> list[ClipRecord]:
    """Read a Clip Labeler CSV and attach rows to matching files in clips_dir."""

    csv_path = Path(csv_path)
    clips_dir = Path(clips_dir)
    if not csv_path.exists():
        raise FileNotFoundError(f"Label CSV not found: {csv_path}")
    if not clips_dir.exists():
        raise FileNotFoundError(f"Clips directory not found: {clips_dir}")

    media_index = _index_media(clips_dir)
    clips: list[ClipRecord] = []
    missing: list[str] = []

    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = (row.get("filename") or "").strip()
            if not filename:
                continue

            path = media_index.get(filename.lower())
            if path is None:
                missing.append(filename)
                continue

            labels = {
                key: _parse_label_value(key, value)
                for key, value in row.items()
                if key not in META_FIELDS
            }
            clips.append(
                ClipRecord(
                    filename=filename,
                    path=path,
                    trim_start=_parse_float(row.get("trim_start"), default=0.0) or 0.0,
                    trim_end=_parse_float(row.get("trim_end"), default=None),
                    notes=(row.get("notes") or "").strip(),
                    labels=labels,
                )
            )

    if missing:
        missing_preview = ", ".join(missing[:8])
        suffix = "" if len(missing) <= 8 else f", +{len(missing) - 8} more"
        print(f"Warning: skipped labels for missing clips: {missing_preview}{suffix}")

    return clips


def _index_media(clips_dir: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in clips_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in VIDEO_EXTS:
            index.setdefault(path.name.lower(), path)
    return index


def _parse_label_value(key: str, raw: str | None) -> LabelValue:
    value = (raw or "").strip()
    if not value:
        return [] if key in MULTI_LABEL_FIELDS else None
    if key in MULTI_LABEL_FIELDS or "|" in value:
        return [part.strip() for part in value.split("|") if part.strip()]
    return value


def _parse_float(raw: str | None, default: float | None) -> float | None:
    value = (raw or "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default
