from __future__ import annotations


GRADE_FILTERS = {
    # Warm, punchy, clean-service look.
    "cleaning": "eq=contrast=1.08:saturation=1.12:brightness=0.015,unsharp=5:5:0.45",
    # Cooler high-contrast look for road work and safety footage.
    "traffic": "eq=contrast=1.14:saturation=1.05:brightness=-0.005,unsharp=5:5:0.5",
    "neutral": "eq=contrast=1.04:saturation=1.04,unsharp=5:5:0.35",
}


def ffmpeg_grade_filter(name: str | None) -> str | None:
    if not name:
        return None
    return GRADE_FILTERS.get(name, GRADE_FILTERS.get("neutral"))
