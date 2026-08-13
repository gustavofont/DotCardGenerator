#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

from card_composer import VALID_RARITIES, VALID_TYPES, compose_card

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = PROJECT_ROOT / "cards.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "GeneratedCards"


def load_config(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"Config file not found: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def safe_filename(name: str) -> str:
    return name.replace("/", "-").replace("\\", "-")


def main():
    parser = argparse.ArgumentParser(description="Generate DotCard card images from a JSON config.")
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
        help="Path to the cards JSON config (default: cards.json)",
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUTPUT_DIR,
        help="Output folder (default: GeneratedCards/)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    images_dir = PROJECT_ROOT / config.get("imagesDir", "SourceArt")
    default_collection = config.get("collection", "")
    cards = config.get("cards", [])

    if not cards:
        sys.exit("No cards found in config — check the 'cards' array in your JSON file.")

    args.out.mkdir(parents=True, exist_ok=True)

    errors = []
    generated = 0
    for i, card in enumerate(cards):
        name = card.get("name")
        card_type = str(card.get("type", "")).upper()
        rarity = str(card.get("rarity", "")).upper()
        collection = card.get("collection", default_collection)
        image_name = card.get("image")

        if not name:
            errors.append(f"[card #{i}] missing 'name'")
            continue
        if card_type not in VALID_TYPES:
            errors.append(f"[{name}] invalid type '{card_type}' — must be one of {sorted(VALID_TYPES)}")
            continue
        if rarity not in VALID_RARITIES:
            errors.append(f"[{name}] invalid rarity '{rarity}' — must be one of {sorted(VALID_RARITIES)}")
            continue
        if not image_name:
            errors.append(f"[{name}] missing 'image'")
            continue

        image_path = images_dir / image_name
        if not image_path.exists():
            errors.append(f"[{name}] image not found: {image_path}")
            continue

        # Same filename as an existing card in GeneratedCards/ -> overwritten
        # by design (Image.save replaces the file outright).
        out_path = args.out / f"{safe_filename(name)}.png"
        try:
            compose_card(str(image_path), name, card_type, rarity, collection, str(out_path))
            try:
                shown_path = out_path.relative_to(PROJECT_ROOT)
            except ValueError:
                shown_path = out_path
            print(f"OK   {name} -> {shown_path}")
            generated += 1
        except Exception as exc:
            errors.append(f"[{name}] failed to generate: {exc}")

    print(f"\n{generated}/{len(cards)} card(s) generated in {args.out}")

    if errors:
        print(f"\n{len(errors)} problem(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
