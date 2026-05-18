# MTW Content Creation Pipeline

This repository turns MTW's raw jobsite footage into labeled, recipe-driven social videos.

It has two parts:

1. **Clip Labeler** - a browser app for importing short raw clips or ZIPs, tagging them with marketing metadata, and exporting `labels/mtw_clip_labels.csv`.
2. **Video Generator** - a Python 3.11+ pipeline that reads those labels, selects clips from a recipe, assembles a timeline, applies platform formatting and MTW color grading, mixes music, and exports a polished video with FFmpeg/MoviePy.

## Quick start

### 1. Install system dependencies

FFmpeg must be installed system-wide.

```bash
# Ubuntu
sudo apt update
sudo apt install ffmpeg
```

### 2. Install Python dependencies

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Label clips

Open the labeler in a browser:

```bash
python -m http.server 8000
```

Then visit:

```text
http://localhost:8000/labeler/
```

Drop raw videos or ZIP files into the app, label each clip, then export the CSV to:

```text
labels/mtw_clip_labels.csv
```

Copy or keep the matching raw footage in:

```text
clips/
```

### 4. Generate a video

```bash
python run.py recipes/cleaning_reel.json
```

The finished video lands in:

```text
output/
```

## Project structure

```text
clips/                  Raw footage, usually exported from phones or job folders
music/                  Royalty-free tracks
assets/                 Logos, fonts, brand graphics
labels/                 CSV exports from the Clip Labeler
recipes/                Video assembly rules
output/                 Rendered videos
labeler/                Browser-based clip labeling app
mtw_pipeline/           Python video generation package
run.py                  CLI entry point
```

## Recipe example

Recipes define what kind of video to build. For example:

```json
{
  "name": "MTW Cleaning - Instagram Reel",
  "division": "mtw_cleaning",
  "platform": "reels_tiktok",
  "duration_target": 30,
  "aspect_ratio": "9:16",
  "music": "music/hype_track_01.mp3",
  "beat_sync": true,
  "color_grade": "cleaning",
  "captions": false,
  "structure": [
    {
      "slot": "hook",
      "duration": 3,
      "filters": { "wow_factor": "hook_worthy", "energy": "high" }
    },
    {
      "slot": "work_montage",
      "duration": 18,
      "clip_count": 4,
      "filters": { "marketing_use": "b_roll", "emotion": ["trust", "professionalism"] }
    }
  ]
}
```

## Output defaults

The exporter uses high-quality H.264 settings intended for social platforms:

- **Reels/TikTok/Shorts:** 1080 x 1920, 30 fps, CRF 18
- **YouTube/Facebook landscape:** 1920 x 1080, 30 fps, CRF 16
- **Audio:** AAC, 192k
- **Pixel format:** yuv420p for platform compatibility

## Notes

- The generator is deterministic by default, so the same recipe and labels produce stable results.
- Beat syncing uses `librosa` when a music file is present and `beat_sync` is enabled.
- Whisper captions are wired as an optional step. The first version leaves captions disabled in sample recipes so the core video pipeline remains fast and predictable.
