# MTW Content Workflow

## 1. Collect footage

Put source footage into `clips/`. Keep the original phone filenames if possible, because the labeler CSV matches rows to files by filename.

Recommended clip length:

- 2-12 seconds for montage B-roll
- 3-8 seconds for hooks
- 5-15 seconds for testimonials or worker explanations

## 2. Label footage

Open `labeler/index.html` through a local server:

```bash
python -m http.server 8000
```

Visit `http://localhost:8000/labeler/`, import raw clips or ZIP files, and label each clip.

Required labels:

- MTW division
- service shown
- energy level
- wow factor
- marketing use

Useful labels for stronger recipe matching:

- context/action
- emotion triggered
- subject in frame
- platform fit
- technical quality

Export the CSV as:

```text
labels/mtw_clip_labels.csv
```

## 3. Choose a recipe

Recipes live in `recipes/`.

Start with:

- `recipes/cleaning_reel.json`
- `recipes/traffic_reel.json`
- `recipes/facebook_ad.json`

Run a dry run first:

```bash
python run.py recipes/cleaning_reel.json --dry-run
```

This shows which clips each slot selected without rendering.

## 4. Render

```bash
python run.py recipes/cleaning_reel.json
```

Rendered videos go into `output/`.

## 5. Improve results

If a slot says `no matches`, update either:

- labels in the CSV, if the footage exists but was not tagged for that use
- recipe filters, if the recipe is too strict

For high-performing content, label hooks and reveals carefully:

- `wow_factor=hook_worthy`
- `marketing_use=scroll_hook`
- `subject=finished_result`
- `emotion=trust|professionalism|safety`

## Music and beat sync

Put royalty-free music in `music/` and point the recipe's `music` field to that file. If `beat_sync` is true, the pipeline uses `librosa` to snap slot timing toward beat timestamps.

## Captions

Set `"captions": true` in a recipe to run local Whisper after the first render and burn captions with FFmpeg. This adds processing time, so leave it off for pure B-roll reels and enable it for testimonials or worker explanations.
