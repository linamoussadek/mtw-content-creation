# Recipe Guide

Recipes are JSON files that describe the finished video.

## Top-level fields

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
  "captions": false
}
```

- `division`: limits the video to Cleaning or Traffic clips.
- `platform`: matches the labeler's Platform Fit field.
- `aspect_ratio`: `9:16`, `16:9`, or `1:1`.
- `music`: optional music file path.
- `beat_sync`: enables `librosa` beat timing when music exists.
- `color_grade`: `cleaning`, `traffic`, or `neutral`.
- `captions`: runs local Whisper and burns captions after rendering.

## Structure slots

Each slot selects one or more clips.

```json
{
  "slot": "work_montage",
  "duration": 18,
  "clip_count": 4,
  "filters": {
    "marketing_use": "b_roll",
    "emotion": ["trust", "professionalism"]
  }
}
```

Filter behavior:

- scalar labels match exact values
- multi labels match any expected value
- lists in recipes are treated as "match any"
- selected clips are sorted by technical quality labels

## End card

```json
{
  "end_card": {
    "duration": 3,
    "logo": "assets/logo_cleaning.png",
    "text": "mtwservices.com | 613-668-2215"
  }
}
```

The renderer generates a branded MTW end card in code and composites the transparent PNG from `logo` when that asset exists.
