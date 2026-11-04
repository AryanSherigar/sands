"""Render the Reincarnated Aristocrat map images to the committed assets folder.

Run via:
    python -m scripts.render_aristocrat_maps [--output-dir PATH]

Rendering is deterministic, so re-running leaves git clean unless the layouts or
the scenery changed. Pillow is a dev dependency only.
"""

import argparse
from pathlib import Path

from scripts.reincarnated_aristocrat import maps
from scripts.reincarnated_aristocrat.mapart.constants import MAP_ASSET_DIR
from scripts.reincarnated_aristocrat.mapart.render import render_all


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=MAP_ASSET_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    for path in render_all(maps.map_seeds(with_images=False), args.output_dir):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
