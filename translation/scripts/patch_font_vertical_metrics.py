from __future__ import annotations

import argparse
import struct
from pathlib import Path


CHECKSUM_MAGIC = 0xB1B0AFBA


def u16(data: bytearray, off: int) -> int:
    return struct.unpack_from(">H", data, off)[0]


def s16(data: bytearray, off: int) -> int:
    return struct.unpack_from(">h", data, off)[0]


def put_u16(data: bytearray, off: int, value: int) -> None:
    struct.pack_into(">H", data, off, value)


def put_s16(data: bytearray, off: int, value: int) -> None:
    if not -32768 <= value <= 32767:
        raise ValueError(f"s16 out of range: {value}")
    struct.pack_into(">h", data, off, value)


def put_u32(data: bytearray, off: int, value: int) -> None:
    struct.pack_into(">I", data, off, value & 0xFFFFFFFF)


def parse_tables(data: bytearray) -> dict[str, tuple[int, int, int]]:
    if len(data) < 12:
        raise ValueError("not a sfnt font")
    num_tables = u16(data, 4)
    tables: dict[str, tuple[int, int, int]] = {}
    for i in range(num_tables):
        rec = 12 + i * 16
        tag = bytes(data[rec : rec + 4]).decode("ascii")
        offset = struct.unpack_from(">I", data, rec + 8)[0]
        length = struct.unpack_from(">I", data, rec + 12)[0]
        if offset + length > len(data):
            raise ValueError(f"table {tag} outside file")
        tables[tag] = (offset, length, rec)
    return tables


def table_checksum(data: bytearray, offset: int, length: int) -> int:
    padded = (length + 3) & ~3
    total = 0
    for pos in range(offset, offset + padded, 4):
        word = bytes(data[pos : pos + 4])
        if len(word) < 4:
            word = word + b"\0" * (4 - len(word))
        total = (total + struct.unpack(">I", word)[0]) & 0xFFFFFFFF
    return total


def whole_font_checksum(data: bytearray) -> int:
    total = 0
    for pos in range(0, (len(data) + 3) & ~3, 4):
        word = bytes(data[pos : pos + 4])
        if len(word) < 4:
            word = word + b"\0" * (4 - len(word))
        total = (total + struct.unpack(">I", word)[0]) & 0xFFFFFFFF
    return total


def update_checksums(data: bytearray, tables: dict[str, tuple[int, int, int]]) -> None:
    head_off, _, _ = tables["head"]
    put_u32(data, head_off + 8, 0)
    for _, (offset, length, rec) in tables.items():
        put_u32(data, rec + 4, table_checksum(data, offset, length))
    adjustment = (CHECKSUM_MAGIC - whole_font_checksum(data)) & 0xFFFFFFFF
    put_u32(data, head_off + 8, adjustment)
    _, head_len, head_rec = tables["head"]
    put_u32(data, head_rec + 4, table_checksum(data, head_off, head_len))


def patch_font(src: Path, dst: Path, factor: float, desc_factor: float) -> None:
    data = bytearray(src.read_bytes())
    tables = parse_tables(data)
    for required in ("head", "hhea", "OS/2"):
        if required not in tables:
            raise ValueError(f"{src}: missing {required} table")

    head = tables["head"][0]
    hhea = tables["hhea"][0]
    os2 = tables["OS/2"][0]
    units_per_em = u16(data, head + 18)

    target_total = max(1, round(units_per_em * factor))
    descent_abs = max(1, round(units_per_em * desc_factor))
    if descent_abs >= target_total:
        raise ValueError("descender is larger than target total height")
    ascender = target_total - descent_abs
    descender = -descent_abs

    old = {
        "hhea": (s16(data, hhea + 4), s16(data, hhea + 6), s16(data, hhea + 8)),
        "typo": (s16(data, os2 + 68), s16(data, os2 + 70), s16(data, os2 + 72)),
        "win": (u16(data, os2 + 74), u16(data, os2 + 76)),
    }

    put_s16(data, hhea + 4, ascender)
    put_s16(data, hhea + 6, descender)
    put_s16(data, hhea + 8, 0)
    put_s16(data, os2 + 68, ascender)
    put_s16(data, os2 + 70, descender)
    put_s16(data, os2 + 72, 0)
    put_u16(data, os2 + 74, ascender)
    put_u16(data, os2 + 76, descent_abs)

    fs_selection = u16(data, os2 + 62)
    put_u16(data, os2 + 62, fs_selection | (1 << 7))

    update_checksums(data, tables)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)

    print(
        f"{src.name}: units={units_per_em}, old hhea={old['hhea']}, "
        f"old typo={old['typo']}, old win={old['win']} -> "
        f"asc={ascender}, desc={descender}, gap=0, win=({ascender},{descent_abs})"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--factor", type=float, default=1.08)
    ap.add_argument("--desc-factor", type=float, default=0.16)
    args = ap.parse_args()
    patch_font(args.src, args.dst, args.factor, args.desc_factor)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
