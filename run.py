from __future__ import annotations

import argparse
from pathlib import Path

from mtw_pipeline import generate_video


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an MTW marketing video from a recipe.")
    parser.add_argument("recipe", help="Path to a recipe JSON file, for example recipes/cleaning_reel.json")
    parser.add_argument("--labels", default="labels/mtw_clip_labels.csv", help="CSV exported from the Clip Labeler")
    parser.add_argument("--clips-dir", default="clips", help="Directory containing raw footage")
    parser.add_argument("--output-dir", default="output", help="Directory for rendered videos")
    parser.add_argument("--dry-run", action="store_true", help="Show selected clips without rendering")
    args = parser.parse_args()

    plan = generate_video(
        recipe_path=args.recipe,
        labels_path=args.labels,
        clips_dir=args.clips_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )

    print(f"Recipe: {plan.recipe.get('name')}")
    for selection in plan.selections:
        names = ", ".join(clip.filename for clip in selection.clips) or "no matches"
        print(f"- {selection.slot}: {names}")

    if args.dry_run:
        print(f"Dry run complete. Output would be: {Path(plan.output_path)}")
    else:
        print(f"Rendered: {Path(plan.output_path)}")


if __name__ == "__main__":
    main()
