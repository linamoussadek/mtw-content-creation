from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


LabelValue = str | list[str] | None


@dataclass(frozen=True)
class ClipRecord:
    """A raw clip plus the labels exported by the browser labeler."""

    filename: str
    path: Path
    trim_start: float = 0.0
    trim_end: float | None = None
    notes: str = ""
    labels: dict[str, LabelValue] = field(default_factory=dict)

    def label(self, key: str) -> LabelValue:
        return self.labels.get(key)


@dataclass(frozen=True)
class SlotSelection:
    """Clips selected for one recipe slot."""

    slot: str
    target_duration: float
    clips: tuple[ClipRecord, ...]
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RenderPlan:
    """The clip order and export settings derived from a recipe."""

    recipe: dict[str, Any]
    selections: tuple[SlotSelection, ...]
    output_path: Path

    @property
    def selected_clips(self) -> tuple[ClipRecord, ...]:
        clips: list[ClipRecord] = []
        for selection in self.selections:
            clips.extend(selection.clips)
        return tuple(clips)
