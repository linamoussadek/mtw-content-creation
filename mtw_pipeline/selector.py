from __future__ import annotations

import random
from typing import Any

from .models import ClipRecord, SlotSelection


def build_selections(clips: list[ClipRecord], recipe: dict[str, Any]) -> tuple[SlotSelection, ...]:
    """Select clips for each recipe slot using the label metadata."""

    rng = random.Random(recipe.get("seed", 42))
    available = _filter_global(clips, recipe)
    used_paths: set[str] = set()
    selections: list[SlotSelection] = []

    for slot in recipe.get("structure", []):
        filters = dict(slot.get("filters") or {})
        candidates = [clip for clip in available if matches_filters(clip, filters)]
        if recipe.get("avoid_reuse", True):
            fresh = [clip for clip in candidates if str(clip.path) not in used_paths]
            if fresh:
                candidates = fresh

        ranked = sorted(candidates, key=_quality_score, reverse=True)
        clip_count = int(slot.get("clip_count") or 1)
        if slot.get("shuffle", False):
            rng.shuffle(ranked)

        selected = tuple(ranked[:clip_count])
        used_paths.update(str(clip.path) for clip in selected)
        selections.append(
            SlotSelection(
                slot=str(slot.get("slot") or "unnamed"),
                target_duration=float(slot.get("duration") or 0),
                clips=selected,
                filters=filters,
            )
        )

    return tuple(selections)


def matches_filters(clip: ClipRecord, filters: dict[str, Any]) -> bool:
    return all(_matches_value(clip.label(key), expected) for key, expected in filters.items())


def _filter_global(clips: list[ClipRecord], recipe: dict[str, Any]) -> list[ClipRecord]:
    filters: dict[str, Any] = {}
    if recipe.get("division"):
        filters["division"] = recipe["division"]
    if recipe.get("platform"):
        filters["platform"] = recipe["platform"]

    return [clip for clip in clips if matches_filters(clip, filters)]


def _matches_value(actual: Any, expected: Any) -> bool:
    if expected is None:
        return True
    if actual is None:
        return False

    actual_values = actual if isinstance(actual, list) else [actual]
    expected_values = expected if isinstance(expected, list) else [expected]
    return bool(set(map(str, actual_values)) & set(map(str, expected_values)))


def _quality_score(clip: ClipRecord) -> int:
    quality = clip.label("quality")
    values = set(quality if isinstance(quality, list) else [quality])
    score = 0
    score += 2 if "sharp" in values else 0
    score += 2 if "well_lit" in values else 0
    score += 1 if "clean_audio" in values else 0
    score -= 2 if "shaky" in values else 0
    score -= 1 if "dark" in values else 0
    score -= 1 if "noisy_audio" in values else 0
    return score
