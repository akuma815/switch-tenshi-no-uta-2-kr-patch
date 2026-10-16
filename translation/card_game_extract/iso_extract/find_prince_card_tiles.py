"""Locate the actual PRINCE card bitmap tiles in Track02.iso."""

from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
ISO = ROOT / "translation/card_game_extract/gamepack/Emulator_Tenshinouta/Content/Ogix/GamePack/install/Tenshi2/Track02.iso"
SCREENSHOT = Path(
    r"C:\Users\akuma\.gemini\antigravity-ide\brain"
    r"\0c483edb-11bf-43da-8263-c5d2a24522bb\media__1784686968964.png"
)
START = 6080 * 2048
END = 6154 * 2048


def decode_tiles(raw: bytes) -> np.ndarray:
    source = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 32)
    tiles = np.zeros((len(source), 8, 8), dtype=np.uint8)
    for y in range(8):
        bit0 = source[:, y * 2]
        bit1 = source[:, y * 2 + 1]
        bit2 = source[:, 16 + y * 2]
        bit3 = source[:, 17 + y * 2]
        for x in range(8):
            shift = 7 - x
            tiles[:, y, x] = (
                ((bit0 >> shift) & 1)
                | (((bit1 >> shift) & 1) << 1)
                | (((bit2 >> shift) & 1) << 2)
                | (((bit3 >> shift) & 1) << 3)
            )
    return tiles


def decode_sprites(raw: bytes, little_endian: bool) -> np.ndarray:
    source = np.frombuffer(raw[:len(raw) // 128 * 128], dtype=np.uint8).reshape(-1, 128)
    sprites = np.zeros((len(source), 16, 16), dtype=np.uint8)
    for y in range(16):
        for plane in range(4):
            lo = source[:, plane * 32 + y * 2]
            hi = source[:, plane * 32 + y * 2 + 1]
            words = lo.astype(np.uint16) | (hi.astype(np.uint16) << 8)
            if not little_endian:
                words = hi.astype(np.uint16) | (lo.astype(np.uint16) << 8)
            for x in range(16):
                sprites[:, y, x] |= (((words >> (15 - x)) & 1) << plane).astype(np.uint8)
    return sprites


def native_prince() -> np.ndarray:
    screen_image = Image.open(SCREENSHOT).convert("RGB")
    # Exact 4x nearest-neighbour card bounds in the 1024x768 capture.
    crop = screen_image.crop((416, 536, 544, 688)).quantize(
        colors=16, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
    ).convert("RGB")
    return np.asarray(crop)[::4, ::4]


def render_candidate(candidate: np.ndarray, target: np.ndarray, path: Path) -> None:
    rendered = np.zeros((*candidate.shape, 3), dtype=np.uint8)
    target_flat = target.reshape(-1, 3)
    for palette_index in range(16):
        mask = candidate == palette_index
        if not mask.any():
            continue
        values, counts = np.unique(target_flat[mask.reshape(-1)], axis=0, return_counts=True)
        rendered[mask] = values[counts.argmax()]
    comparison = np.concatenate((target, rendered), axis=1)
    Image.fromarray(comparison).resize(
        (comparison.shape[1] * 8, comparison.shape[0] * 8), Image.Resampling.NEAREST
    ).save(path)


def score(candidate: np.ndarray, target: np.ndarray) -> float:
    """Palette-independent pixel agreement; each 4bpp index maps to one RGB color."""
    colors, target_ids = np.unique(target.reshape(-1, 3), axis=0, return_inverse=True)
    target_ids = target_ids.reshape(target.shape[:2])
    matched = 0
    for palette_index in range(16):
        mask = candidate == palette_index
        if mask.any():
            counts = np.bincount(target_ids[mask], minlength=len(colors))
            matched += int(counts.max())
    return matched / candidate.size


def score_all_tiles(tiles: np.ndarray, target: np.ndarray) -> np.ndarray:
    colors, target_ids = np.unique(target.reshape(-1, 3), axis=0, return_inverse=True)
    target_ids = target_ids.reshape(8, 8)
    scores = np.zeros(len(tiles), dtype=np.int16)
    for tile_number, tile in enumerate(tiles):
        matched = 0
        for palette_index in range(16):
            mask = tile == palette_index
            if mask.any():
                counts = np.bincount(target_ids[mask], minlength=len(colors))
                matched += int(counts.max())
        scores[tile_number] = matched
    return scores


def assemble(tiles: np.ndarray, start: int, layout: str) -> np.ndarray:
    if layout == "row":
        indices = np.arange(start, start + 20).reshape(5, 4)
    elif layout == "column":
        indices = np.arange(start, start + 20).reshape(4, 5).T
    elif layout == "stride16":
        indices = start + np.arange(5)[:, None] * 16 + np.arange(4)[None, :]
    else:
        raise ValueError(layout)
    rows = [np.concatenate([tiles[i] for i in row], axis=1) for row in indices]
    return np.concatenate(rows, axis=0)


def assemble_sprites(sprites: np.ndarray, start: int, layout: str) -> np.ndarray:
    if layout == "row":
        indices = np.arange(start, start + 6).reshape(3, 2)
    else:
        indices = np.arange(start, start + 6).reshape(2, 3).T
    rows = [np.concatenate([sprites[i] for i in row], axis=1) for row in indices]
    return np.concatenate(rows, axis=0)


def main() -> None:
    data = ISO.read_bytes()
    tiles = decode_tiles(data[START:END])
    target = native_prince()
    sprite_results = []
    for endian_name, little_endian in (("le", True), ("be", False)):
        sprites = decode_sprites(data[START:END], little_endian)
        for layout in ("row", "column"):
            for sprite_index in range(len(sprites) - 6):
                image = assemble_sprites(sprites, sprite_index, layout)
                for y_offset in range(11):
                    value = score(image[y_offset:y_offset + 38], target)
                    sprite_results.append(
                        (value, endian_name, layout, sprite_index, y_offset)
                    )
    sprite_results.sort(reverse=True)
    print("16x16 sprite matches:")
    for value, endian_name, layout, sprite_index, y_offset in sprite_results[:12]:
        absolute = START + sprite_index * 128
        print(
            f"score={value:.5f} endian={endian_name} layout={layout:6s} "
            f"sprite={sprite_index:4d} offset=0x{absolute:08X} y={y_offset}"
        )
    print("individual 8x8 matches:")
    for grid_y in range(4):
        line = []
        for grid_x in range(4):
            target_tile = target[grid_y * 8:(grid_y + 1) * 8, grid_x * 8:(grid_x + 1) * 8]
            tile_scores = score_all_tiles(tiles, target_tile)
            best = np.argsort(tile_scores)[-3:][::-1]
            matches = "/".join(
                f"{index}@0x{START + int(index) * 32:08X}:{tile_scores[index] / 64:.3f}"
                for index in best
            )
            line.append(f"({grid_x},{grid_y}) {matches}")
        print(" | ".join(line))
    results = []
    limits = {
        "row": len(tiles) - 20,
        "column": len(tiles) - 20,
        "stride16": len(tiles) - (4 * 16 + 4),
    }
    for layout, limit in limits.items():
        for tile_index in range(limit):
            image = assemble(tiles, tile_index, layout)
            for y_offset in range(3):
                value = score(image[y_offset:y_offset + 38], target)
                results.append((value, layout, tile_index, y_offset))

    results.sort(reverse=True)
    print(f"target={target.shape[1]}x{target.shape[0]} colors={len(np.unique(target.reshape(-1, 3), axis=0))}")
    for value, layout, tile_index, y_offset in results[:12]:
        absolute = START + tile_index * 32
        print(
            f"score={value:.5f} layout={layout:8s} tile={tile_index:4d} "
            f"offset=0x{absolute:08X} y={y_offset}"
        )
    value, layout, tile_index, y_offset = results[0]
    best = assemble(tiles, tile_index, layout)[y_offset:y_offset + 38]
    output = Path(__file__).with_name("prince_card_match.png")
    render_candidate(best, target, output)
    print(f"comparison={output}")


if __name__ == "__main__":
    main()
