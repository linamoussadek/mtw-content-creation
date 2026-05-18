from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .audio import beat_times, nearest_beat_duration
from .captions import burn_srt, transcribe_to_srt
from .exporter import platform_export_profile
from .grader import ffmpeg_grade_filter
from .labeler import load_clip_labels
from .models import ClipRecord, RenderPlan
from .selector import build_selections


def generate_video(
    recipe_path: str | Path,
    labels_path: str | Path = "labels/mtw_clip_labels.csv",
    clips_dir: str | Path = "clips",
    output_dir: str | Path = "output",
    dry_run: bool = False,
) -> RenderPlan:
    """Build and optionally render a video from a JSON recipe."""

    recipe_path = Path(recipe_path)
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    clips = load_clip_labels(labels_path, clips_dir)
    selections = build_selections(clips, recipe)
    output_path = _output_path(recipe, output_dir)
    plan = RenderPlan(recipe=recipe, selections=selections, output_path=output_path)

    _validate_plan(plan)
    if dry_run:
        return plan

    _render_plan(plan)
    return plan


def _render_plan(plan: RenderPlan) -> None:
    moviepy = _import_moviepy()
    settings = _export_settings(plan.recipe)
    output_path = plan.output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    beats = _load_beats(plan.recipe)
    video_clips = []
    open_clips = []

    try:
        for selection in plan.selections:
            if not selection.clips:
                continue
            slot_duration = _slot_duration(selection.target_duration, beats, plan.recipe)
            per_clip = slot_duration / len(selection.clips)
            for clip_record in selection.clips:
                clip = _prepare_clip(moviepy, clip_record, per_clip, settings["resolution"])
                video_clips.append(clip)
                open_clips.append(clip)

        if not video_clips:
            raise RuntimeError("Recipe did not select any renderable clips.")

        end_card = _make_end_card(moviepy, plan.recipe, settings["resolution"])
        if end_card is not None:
            video_clips.append(end_card)
            open_clips.append(end_card)

        final = moviepy.concatenate_videoclips(video_clips, method="compose")
        final = _with_fps(final, settings["fps"])
        final = _apply_music(moviepy, final, plan.recipe)

        ffmpeg_params = ["-pix_fmt", "yuv420p", "-crf", str(settings["crf"])]
        grade_filter = ffmpeg_grade_filter(plan.recipe.get("color_grade"))
        if grade_filter:
            ffmpeg_params = ["-vf", grade_filter, *ffmpeg_params]

        final.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            audio_bitrate="192k",
            fps=settings["fps"],
            preset=settings["preset"],
            ffmpeg_params=ffmpeg_params,
        )
        if plan.recipe.get("captions"):
            _caption_render(output_path, plan.recipe)
        _close_clip(final)
    finally:
        for clip in open_clips:
            _close_clip(clip)


def _caption_render(output_path: Path, recipe: dict[str, Any]) -> None:
    srt_path = output_path.with_suffix(".srt")
    captioned_path = output_path.with_name(f"{output_path.stem}_captioned{output_path.suffix}")
    transcribe_to_srt(output_path, srt_path, model_name=str(recipe.get("whisper_model") or "base"))
    burn_srt(output_path, srt_path, captioned_path)
    captioned_path.replace(output_path)


def _prepare_clip(moviepy: Any, record: ClipRecord, target_duration: float, resolution: tuple[int, int]) -> Any:
    source = moviepy.VideoFileClip(str(record.path))
    start = max(record.trim_start, 0.0)
    source_duration = float(getattr(source, "duration", 0) or 0)
    natural_end = record.trim_end if record.trim_end and record.trim_end > start else source_duration
    end = min(natural_end, start + target_duration) if source_duration else natural_end
    if end <= start:
        end = min(source_duration, start + target_duration) if source_duration else start + target_duration

    clip = _subclip(source, start, end)
    clip = _resize_to_cover(clip, resolution)
    clip = _without_audio(clip)
    return clip


def _resize_to_cover(clip: Any, resolution: tuple[int, int]) -> Any:
    target_w, target_h = resolution
    width = float(getattr(clip, "w", getattr(clip, "size", [target_w, target_h])[0]))
    height = float(getattr(clip, "h", getattr(clip, "size", [target_w, target_h])[1]))
    scale = max(target_w / width, target_h / height)
    new_size = (round(width * scale), round(height * scale))

    if hasattr(clip, "resized"):
        clip = clip.resized(new_size=new_size)
    else:
        clip = clip.resize(newsize=new_size)

    new_w = float(getattr(clip, "w", new_size[0]))
    new_h = float(getattr(clip, "h", new_size[1]))
    x_center = new_w / 2
    y_center = new_h / 2
    if hasattr(clip, "cropped"):
        return clip.cropped(x_center=x_center, y_center=y_center, width=target_w, height=target_h)
    return clip.crop(x_center=x_center, y_center=y_center, width=target_w, height=target_h)


def _apply_music(moviepy: Any, final: Any, recipe: dict[str, Any]) -> Any:
    music = recipe.get("music")
    if not music:
        return final
    music_path = Path(music)
    if not music_path.exists():
        print(f"Warning: music file not found, exporting without music: {music_path}")
        return final

    audio = moviepy.AudioFileClip(str(music_path))
    duration = float(getattr(final, "duration", 0) or 0)
    audio = _loop_audio(moviepy, audio, duration)
    audio = _with_duration(audio, duration)
    return _with_audio(final, audio)


def _loop_audio(moviepy: Any, audio: Any, duration: float) -> Any:
    audio_duration = float(getattr(audio, "duration", 0) or 0)
    if not audio_duration or audio_duration >= duration:
        return _subclip(audio, 0, duration)

    pieces = []
    start = 0.0
    while start < duration:
        piece = _with_start(audio.copy(), start)
        pieces.append(piece)
        start += audio_duration
    return moviepy.CompositeAudioClip(pieces)


def _make_end_card(moviepy: Any, recipe: dict[str, Any], resolution: tuple[int, int]) -> Any | None:
    end_card = recipe.get("end_card")
    if not end_card:
        return None

    try:
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("End cards require Pillow and numpy. Install dependencies with pip install -r requirements.txt") from exc

    width, height = resolution
    image = Image.new("RGB", (width, height), "#050505")
    draw = ImageDraw.Draw(image)
    green = "#5dfc2a"
    white = "#f0f0f0"
    muted = "#777777"

    title_font = _font(ImageFont, size=max(72, width // 11), bold=True)
    body_font = _font(ImageFont, size=max(36, width // 28), bold=False)

    logo_path = Path(str(end_card.get("logo") or ""))
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
        max_logo_w = int(width * 0.34)
        max_logo_h = int(height * 0.16)
        logo.thumbnail((max_logo_w, max_logo_h))
        pos = ((width - logo.width) // 2, int(height * 0.32))
        image.paste(logo, pos, logo)
        title_y = height * 0.48
    else:
        title_y = height * 0.42

    draw.text((width / 2, title_y), "MTW", fill=green, font=title_font, anchor="mm")
    draw.text((width / 2, height * 0.51), str(end_card.get("text", "")), fill=white, font=body_font, anchor="mm")
    draw.text((width / 2, height * 0.58), str(recipe.get("name", "")), fill=muted, font=body_font, anchor="mm")

    clip = moviepy.ImageClip(np.asarray(image))
    return _with_duration(clip, float(end_card.get("duration") or 3))


def _font(image_font: Any, size: int, bold: bool) -> Any:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        try:
            return image_font.truetype(candidate, size=size)
        except OSError:
            continue
    return image_font.load_default()


def _load_beats(recipe: dict[str, Any]) -> list[float]:
    music = recipe.get("music")
    if not recipe.get("beat_sync") or not music or not Path(music).exists():
        return []
    try:
        return beat_times(music)
    except RuntimeError as exc:
        print(f"Warning: {exc}")
        return []


def _slot_duration(target_duration: float, beats: list[float], recipe: dict[str, Any]) -> float:
    if not recipe.get("beat_sync") or not beats:
        return target_duration
    return nearest_beat_duration(target_duration, beats)


def _validate_plan(plan: RenderPlan) -> None:
    empty = [selection.slot for selection in plan.selections if not selection.clips]
    if empty:
        print(f"Warning: no clips matched these slots: {', '.join(empty)}")
    if not plan.selected_clips:
        raise RuntimeError("No clips matched this recipe. Check labels, platform, division, and slot filters.")
    minimum = int(plan.recipe.get("minimum_clip_count") or 1)
    unique_count = len({str(clip.path) for clip in plan.selected_clips})
    if unique_count < minimum:
        raise RuntimeError(
            f"This recipe needs at least {minimum} unique clip(s), but only {unique_count} matched. "
            "Import/label more clips or use a more relaxed recipe."
        )


def _output_path(recipe: dict[str, Any], output_dir: str | Path) -> Path:
    output_dir = Path(output_dir)
    slug = "".join(ch if ch.isalnum() else "_" for ch in str(recipe.get("name") or "mtw_video").lower())
    slug = "_".join(part for part in slug.split("_") if part)
    return output_dir / f"{slug}.mp4"


def _export_settings(recipe: dict[str, Any]) -> dict[str, Any]:
    profile = platform_export_profile(recipe)
    return {
        "resolution": tuple(recipe.get("resolution") or profile["resolution"]),
        "fps": int(recipe.get("fps") or profile["fps"]),
        "crf": int(recipe.get("crf") or profile["crf"]),
        "preset": str(recipe.get("preset") or profile["preset"]),
    }


def _import_moviepy() -> Any:
    try:
        import moviepy
        from moviepy import AudioFileClip, CompositeAudioClip, ImageClip, VideoFileClip, concatenate_videoclips
    except ImportError:
        try:
            from moviepy.editor import AudioFileClip, CompositeAudioClip, ImageClip, VideoFileClip, concatenate_videoclips
        except ImportError as exc:
            raise RuntimeError("MoviePy is required. Install dependencies with pip install -r requirements.txt") from exc
        return _MoviePy(AudioFileClip, CompositeAudioClip, ImageClip, VideoFileClip, concatenate_videoclips)

    return _MoviePy(AudioFileClip, CompositeAudioClip, ImageClip, VideoFileClip, concatenate_videoclips)


class _MoviePy:
    def __init__(
        self,
        AudioFileClip: Any,
        CompositeAudioClip: Any,
        ImageClip: Any,
        VideoFileClip: Any,
        concatenate_videoclips: Any,
    ) -> None:
        self.AudioFileClip = AudioFileClip
        self.CompositeAudioClip = CompositeAudioClip
        self.ImageClip = ImageClip
        self.VideoFileClip = VideoFileClip
        self.concatenate_videoclips = concatenate_videoclips


def _subclip(clip: Any, start: float, end: float) -> Any:
    if hasattr(clip, "subclipped"):
        return clip.subclipped(start, end)
    return clip.subclip(start, end)


def _with_duration(clip: Any, duration: float) -> Any:
    if hasattr(clip, "with_duration"):
        return clip.with_duration(duration)
    return clip.set_duration(duration)


def _with_start(clip: Any, start: float) -> Any:
    if hasattr(clip, "with_start"):
        return clip.with_start(start)
    return clip.set_start(start)


def _with_audio(clip: Any, audio: Any) -> Any:
    if hasattr(clip, "with_audio"):
        return clip.with_audio(audio)
    return clip.set_audio(audio)


def _with_fps(clip: Any, fps: int) -> Any:
    if hasattr(clip, "with_fps"):
        return clip.with_fps(fps)
    return clip.set_fps(fps)


def _without_audio(clip: Any) -> Any:
    if hasattr(clip, "without_audio"):
        return clip.without_audio()
    return clip.set_audio(None)


def _close_clip(clip: Any) -> None:
    close = getattr(clip, "close", None)
    if callable(close):
        close()
