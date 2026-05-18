from __future__ import annotations

from pathlib import Path


def beat_times(music_path: str | Path) -> list[float]:
    """Return beat timestamps for a music track using librosa when available."""

    try:
        import librosa
    except ImportError as exc:
        raise RuntimeError("Beat sync requires librosa. Install dependencies with pip install -r requirements.txt") from exc

    y, sr = librosa.load(str(music_path), sr=None, mono=True)
    _, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    return [float(t) for t in beats]


def nearest_beat_duration(target: float, beats: list[float], minimum: float = 0.8) -> float:
    """Snap a target slot duration to the nearest useful beat interval."""

    if not beats:
        return target
    candidates = [beat for beat in beats if beat >= minimum]
    if not candidates:
        return target
    return min(candidates, key=lambda beat: abs(beat - target))
