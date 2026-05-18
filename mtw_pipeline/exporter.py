from __future__ import annotations

from typing import Any


def platform_export_profile(recipe: dict[str, Any]) -> dict[str, Any]:
    """Return the social-platform export profile implied by a recipe."""

    aspect = str(recipe.get("aspect_ratio") or "9:16")
    if aspect == "16:9":
        return {"resolution": (1920, 1080), "fps": 30, "crf": 16, "preset": "slow"}
    if aspect == "1:1":
        return {"resolution": (1080, 1080), "fps": 30, "crf": 18, "preset": "slow"}
    return {"resolution": (1080, 1920), "fps": 30, "crf": 18, "preset": "slow"}
