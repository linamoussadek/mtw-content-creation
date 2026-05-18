from __future__ import annotations

from pathlib import Path
import subprocess


def transcribe_to_srt(video_path: str | Path, output_path: str | Path, model_name: str = "base") -> Path:
    """Transcribe a rendered video to SRT with local Whisper.

    The main recipes keep captions disabled by default. This hook is here for
    clips with spoken explanations or testimonials where burned captions are
    worth the additional processing.
    """

    try:
        import whisper
    except ImportError as exc:
        raise RuntimeError("Captions require openai-whisper. Install dependencies with pip install -r requirements.txt") from exc

    model = whisper.load_model(model_name)
    result = model.transcribe(str(video_path), word_timestamps=False)
    output_path = Path(output_path)
    output_path.write_text(_segments_to_srt(result.get("segments", [])), encoding="utf-8")
    return output_path


def burn_srt(video_path: str | Path, srt_path: str | Path, output_path: str | Path) -> Path:
    """Burn SRT captions into a video with FFmpeg."""

    video_path = Path(video_path)
    srt_path = Path(srt_path)
    output_path = Path(output_path)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"subtitles={_ffmpeg_filter_path(srt_path)}",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-preset",
        "slow",
        "-c:a",
        "copy",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)
    return output_path


def _segments_to_srt(segments: list[dict]) -> str:
    blocks: list[str] = []
    for idx, segment in enumerate(segments, start=1):
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        blocks.append(
            "\n".join(
                [
                    str(idx),
                    f"{_srt_time(float(segment.get('start', 0)))} --> {_srt_time(float(segment.get('end', 0)))}",
                    text,
                ]
            )
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def _srt_time(seconds: float) -> str:
    millis = int(round(max(seconds, 0) * 1000))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def _ffmpeg_filter_path(path: Path) -> str:
    # FFmpeg subtitles filter treats ':' and '\' specially inside filter args.
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
