"""Inject translated card-game PNGs into their original Texture2D assets.

Usage: python inject_card_game_png.py <legacy source tree> <PNG dir> <patch tree>
"""

import sys
from pathlib import Path

from PIL import Image

from inject_manual_png import encode, parse_uexp


REL_DIR = Path("Emulator_Tenshinouta/Content/Ogix/Texture/Game_2/InGame/CardGame")


def main():
    source_root = Path(sys.argv[1])
    png_dir = Path(sys.argv[2])
    output_root = Path(sys.argv[3])
    source_dir = source_root / REL_DIR
    output_dir = output_root / REL_DIR

    source_assets = sorted(source_dir.glob("card_game_*.uexp"))
    if not source_assets:
        raise FileNotFoundError(f"card-game source assets not found: {source_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    injected = 0
    for uexp_path in source_assets:
        name = uexp_path.stem
        png_path = png_dir / f"{name}.png"
        uasset_path = source_dir / f"{name}.uasset"
        if not png_path.exists():
            raise FileNotFoundError(f"translated PNG not found: {png_path}")
        if not uasset_path.exists():
            raise FileNotFoundError(f"source uasset not found: {uasset_path}")

        data = bytearray(uexp_path.read_bytes())
        texture_format, width, height, start, payload_size = parse_uexp(bytes(data))
        image = Image.open(png_path).convert("RGBA")
        if image.size != (width, height):
            raise ValueError(
                f"{name}: PNG {image.size} != source texture {width}x{height}"
            )

        payload = encode(texture_format, image)
        if len(payload) != payload_size:
            raise ValueError(
                f"{name}: encoded payload {len(payload)} != source {payload_size}"
            )

        data[start:start + payload_size] = payload
        (output_dir / f"{name}.uexp").write_bytes(data)
        (output_dir / f"{name}.uasset").write_bytes(uasset_path.read_bytes())
        print(f"  {name}: {texture_format} {width}x{height}")
        injected += 1

    print(f"card-game textures injected: {injected}/{len(source_assets)}")


if __name__ == "__main__":
    main()
