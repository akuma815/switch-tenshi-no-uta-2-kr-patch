"""Patch verified 16x16 sprite card labels in the Tenshi 2 Track02 ISO."""

import hashlib
import sys
from pathlib import Path

from PIL import Image


SOURCE_SHA256 = "7566073a2aa1f48e7b39ed2b34277d9935fade8a3fad7dcc72c21276e2632af9"
SPRITE_SIZE = 128
BACKGROUND_INDEX = 0x0F
FOREGROUND_INDEX = 0x01
GLYPH_COLOR = (99, 207, 99)
GLYPH_SHADOW_COLOR = (57, 51, 255)

# Korean strings use escapes so this script remains independent of shell code pages.
CARD_LABELS = (
    ("KING", "\uc655", 0x00BE5200, 0x00BF8F00, False),
    ("GENERAL", "\uc7a5\uad70", 0x00BE6200, 0x00BF6000, False),
    ("QUEEN", "\uc5ec\uc655", 0x00BE7200, 0x00BF7000, False),
    ("DRAGON", "\uc6a9", 0x00BE7500, 0x00BF7300, False),
    ("PRIEST", "\uc0ac\uc81c", 0x00BE7600, 0x00BF5600, False),
    ("PRINCESS", "\uacf5\uc8fc", 0x00BE7A00, 0x00BF7800, False),
    ("DARK_KNIGHT", "\uc554\ud751\uae30\uc0ac", 0x00BE7D00, 0x00BF7B00, True),
    ("MAID", "\uc2dc\ub140", 0x00BE8200, 0x00BF8000, False),
    ("BERSERKER", "\uad11\uc804\uc0ac", 0x00BE8500, 0x00BF8300, True),
    ("ELF", "\uc5d8\ud504", 0x00BE8600, 0x00BF9600, False),
    ("TOWER", "\ud0d1", 0x00BE8700, 0x00BFA600, False),
    ("ORB", "\ubcf4\uc8fc", 0x00BE8A00, 0x00BF8800, False),
    ("STAFF", "\uc9c0\ud321\uc774", 0x00BE8E00, 0x00BF9E00, False),
    ("SAGE", "\ud604\uc790", 0x00BE9500, 0x00BF9300, False),
    ("HERO", "\uc601\uc6c5", 0x00BEA200, 0x00BFA000, False),
    ("EX_CALIBUR", "\uc5d1\uc2a4\uce7c\ub9ac\ubc84", 0x00BEA500, 0x00BFA300, True),
    ("DARK_MIRROR", "\uc554\ud751\uacbd", 0x00BE9200, 0x00BF9000, True),
    ("GUILD", "\uae38\ub4dc", 0x00BEAD00, 0x00BFAB00, False),
    ("HARLOCK", "\ud751\ub9c8\ubc95\uc0ac", 0x00BE9D00, 0x00BF9B00, False),
    ("REALM", "\uc601\uc9c0", 0x00BE6A00, 0x00BF6800, False),
    ("PARACE", "\uad81\uc804", 0x00BE8D00, 0x00BF8B00, False),
    ("SHRINE", "\uc2e0\uc804", 0x00BE7F00, 0x00BF6E00, False),
    ("SAINT", "\uc131\ub140", 0x00BE7700, 0x00BF5E00, False),
    ("FORTRESS", "\uc694\uc0c8", 0x00BE9A00, 0x00BF9800, False),
    ("PRINCE", "\uc655\uc790", 0x00BE5A00, 0x00BF5800, False),
    ("PALADIN", "\uc131\uae30\uc0ac", 0x00BEAA00, 0x00BFA800, False),
    ("CASTLE", "\uc131", 0x00BE6500, 0x00BF6300, False),
    ("HOLY_SYMBOL", "\uc131\ud45c", 0x00BE7E00, 0x00BF6600, True),
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def decode_sprite(data):
    if len(data) != SPRITE_SIZE:
        raise ValueError("a PCE sprite must be exactly 128 bytes")
    pixels = [[0] * 16 for _ in range(16)]
    for y in range(16):
        for plane in range(4):
            offset = plane * 32 + y * 2
            word = data[offset] | (data[offset + 1] << 8)
            for x in range(16):
                pixels[y][x] |= ((word >> (15 - x)) & 1) << plane
    return pixels


def encode_sprite(pixels):
    data = bytearray(SPRITE_SIZE)
    for y in range(16):
        for plane in range(4):
            word = 0
            for x in range(16):
                word |= ((pixels[y][x] >> plane) & 1) << (15 - x)
            offset = plane * 32 + y * 2
            data[offset] = word & 0xFF
            data[offset + 1] = word >> 8
    return bytes(data)


def decode_pair(data, offset):
    left = decode_sprite(data[offset:offset + SPRITE_SIZE])
    right = decode_sprite(data[offset + SPRITE_SIZE:offset + 2 * SPRITE_SIZE])
    return [left[y] + right[y] for y in range(16)]


def encode_pair(data, offset, pixels):
    left = [row[:16] for row in pixels]
    right = [row[16:] for row in pixels]
    data[offset:offset + SPRITE_SIZE] = encode_sprite(left)
    data[offset + SPRITE_SIZE:offset + 2 * SPRITE_SIZE] = encode_sprite(right)


def load_glyph(font_atlas, character, width, height=8):
    encoded = character.encode("euc_kr")
    lead, trail = encoded
    index = (lead - 0xB0) * 94 + trail - 0xA1
    source_cell = font_atlas.width // 64
    if source_cell not in (8, 10, 16):
        raise ValueError(f"unsupported card font cell size: {source_cell}")
    x = (index % 64) * source_cell
    y = (index // 64) * source_cell
    tile = font_atlas.crop((x, y, x + source_cell, y + source_cell))
    mask = Image.new("1", (source_cell, source_cell))
    mask_pixels = mask.load()
    has_shadow = False
    for py in range(source_cell):
        for px in range(source_cell):
            color = tile.getpixel((px, py))[:3]
            if color == GLYPH_COLOR:
                mask_pixels[px, py] = 1
            elif color == GLYPH_SHADOW_COLOR and px > 0 and py > 0:
                has_shadow = True
                # The atlas stores a one-pixel lower-right shadow. Some edge
                # strokes survive only in that layer, so recover their source
                # pixel before resizing the glyph.
                mask_pixels[px - 1, py - 1] = 1
    if (width, height) != (source_cell, source_cell):
        if source_cell == 16 or not has_shadow:
            # Thin one-pixel strokes disappear with nearest-neighbor reduction.
            # Area sampling plus a low threshold preserves any meaningful part
            # of a stroke covered by the destination pixel.
            mask = mask.convert("L").resize((width, height), Image.Resampling.BOX)
            mask = mask.point(lambda value: 255 if value >= 32 else 0).convert("1")
        else:
            mask = mask.resize((width, height), Image.Resampling.NEAREST)
    return [
        [bool(mask.getpixel((px, py))) for px in range(width)]
        for py in range(height)
    ]


def replace_label(pair, text, view, source_was_two_lines, font_atlas):
    line = text.replace("\n", "")
    wide_clear = source_was_two_lines
    source_cell = font_atlas.width // 64
    if source_cell >= 16:
        glyph_height = 12
    elif source_cell >= 10:
        glyph_height = 10
    else:
        glyph_height = 8
    if view:
        if glyph_height == 12:
            clear_y0, clear_y1, draw_y = 2, 16, 3
        elif glyph_height == 10:
            clear_y0, clear_y1, draw_y = 3, 16, 4
        else:
            clear_y0, clear_y1 = (4, 16) if wide_clear else (4, 12)
            draw_y = 4
    else:
        if glyph_height == 12:
            clear_y0, clear_y1, draw_y = 2, 16, 3
        elif glyph_height == 10:
            clear_y0, clear_y1, draw_y = 2, 15, 4
        else:
            clear_y0, clear_y1 = (2, 14) if wide_clear else (6, 14)
            draw_y = 6

    for y in range(clear_y0, clear_y1):
        # English labels reach farther toward the frame than short Korean labels.
        # Preserve only the outer two frame columns on each side.
        full_width_labels = {
            "\uc5d1\uc2a4\uce7c\ub9ac\ubc84",
            "\ud751\ub9c8\ubc95\uc0ac",
            "\uc554\ud751\uae30\uc0ac",
        }
        use_full_width = line in full_width_labels and glyph_height >= 10
        clear_x0 = 0 if use_full_width else (1 if glyph_height >= 10 else 2)
        for x in range(clear_x0, 32 - clear_x0):
            pair[y][x] = BACKGROUND_INDEX

    # Keep the full glyph height so final consonants remain legible. Long
    # labels are compressed horizontally only and always stay on one line.
    if glyph_height == 12:
        if len(line) >= 5:
            glyph_width, glyph_gap = 6, 0
        elif len(line) == 4:
            glyph_width, glyph_gap = 7, 0
        elif len(line) == 3:
            glyph_width, glyph_gap = 9, 1
        else:
            glyph_width, glyph_gap = 12, 1 if len(line) > 1 else 0
    elif glyph_height == 10:
        if len(line) >= 5:
            glyph_width, glyph_gap = 6, 0
        elif len(line) == 4:
            glyph_width, glyph_gap = 7, 0
        elif len(line) == 3:
            glyph_width, glyph_gap = 8, 1
        else:
            glyph_width, glyph_gap = 10, 1 if len(line) > 1 else 0
    else:
        if len(line) >= 5:
            glyph_width, glyph_gap = 5, 0
        elif len(line) == 4:
            glyph_width, glyph_gap = 6, 0
        elif len(line) == 3:
            glyph_width, glyph_gap = 7, 1
        else:
            glyph_width, glyph_gap = 8, 1 if len(line) > 1 else 0

    glyph_widths = [glyph_width] * len(line)
    if line == "\uc5d1\uc2a4\uce7c\ub9ac\ubc84" and glyph_height >= 10:
        # Use both normally reserved edge pixels for the most complex first
        # syllable: 8 + 6 + 6 + 6 + 6 = the full 32-pixel label width.
        glyph_widths[0] += 2
    elif line == "\ud751\ub9c8\ubc95\uc0ac" and glyph_height >= 10:
        # Spend the four spare pixels on the two syllables that lose the most
        # definition at 7 px: 7 + 9 + 7 + 9 = 32.
        glyph_widths[1] += 2
        glyph_widths[3] += 2
    elif line == "\uc554\ud751\uae30\uc0ac" and glyph_height >= 10:
        # Split the four spare pixels between the dense edge syllables:
        # 9 + 7 + 7 + 9 = 32.
        glyph_widths[0] += 2
        glyph_widths[3] += 2
    elif line == "\uc131\uae30\uc0ac" and glyph_height >= 10:
        # Preserve the round final consonant in the first syllable:
        # 10 + 8 + 8, plus two one-pixel gaps = 28.
        glyph_widths[0] += 2
    elif line == "\uc9c0\ud321\uc774" and glyph_height >= 10:
        # Preserve the round final consonant in the middle syllable:
        # 8 + 10 + 8, plus two one-pixel gaps = 28.
        glyph_widths[1] += 2
    elif line == "\uc554\ud751\uacbd" and glyph_height >= 10:
        # Preserve the round final consonant in the last syllable:
        # 8 + 8 + 10, plus two one-pixel gaps = 28.
        glyph_widths[2] += 2
    elif line == "\uad11\uc804\uc0ac" and glyph_height >= 10:
        # Preserve the round final consonant in the first syllable:
        # 10 + 8 + 8, plus two one-pixel gaps = 28.
        glyph_widths[0] += 2

    text_width = sum(glyph_widths) + (len(line) - 1) * glyph_gap
    start_x = (32 - text_width) // 2
    cursor_x = start_x
    for character, character_width in zip(line, glyph_widths):
        glyph = load_glyph(font_atlas, character, character_width, glyph_height)
        for y in range(glyph_height):
            for x in range(character_width):
                if glyph[y][x]:
                    pair[draw_y + y][cursor_x + x] = FOREGROUND_INDEX
        cursor_x += character_width + glyph_gap


def main():
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: patch_track02_korean_cards.py <source Track02.iso> "
            "<Galmuri7_8x8.png> <output Track02.iso>"
        )
    source_path = Path(sys.argv[1])
    font_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])
    original = source_path.read_bytes()
    source_hash = sha256(original)
    if source_hash != SOURCE_SHA256:
        raise ValueError(f"unexpected Track02 source SHA-256: {source_hash}")

    font_atlas = Image.open(font_path).convert("RGBA")
    patched = bytearray(original)
    ranges = []
    for name, text, normal_offset, view_offset, source_was_two_lines in CARD_LABELS:
        for offset, view in ((normal_offset, False), (view_offset, True)):
            pair = decode_pair(original, offset)
            replace_label(pair, text, view, source_was_two_lines, font_atlas)
            encode_pair(patched, offset, pair)
            ranges.append((offset, offset + 2 * SPRITE_SIZE))

    changed_offsets = [i for i, pair in enumerate(zip(original, patched)) if pair[0] != pair[1]]
    if not changed_offsets:
        raise ValueError("Track02 card-name patch did not change any bytes")
    if any(not any(start <= offset < end for start, end in ranges) for offset in changed_offsets):
        raise ValueError("Track02 card-name patch changed bytes outside verified label sprites")
    if len(patched) != len(original):
        raise ValueError("Track02 ISO size changed")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(patched)
    print(f"Track02 sprite labels patched: {len(CARD_LABELS)} cards, normal + card view")
    print(f"changed bytes: {len(changed_offsets)}")
    print(f"source sha256: {source_hash}")
    print(f"output sha256: {sha256(patched)}")


if __name__ == "__main__":
    main()
