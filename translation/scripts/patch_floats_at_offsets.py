"""Patch verified little-endian float constants at exact UEXP byte offsets."""

import struct
import sys
from pathlib import Path


def main(src_path, dst_path, *specs):
    data = bytearray(Path(src_path).read_bytes())
    for spec in specs:
        offset_text, old_text, new_text = spec.split(":")
        offset = int(offset_text)
        old = struct.pack("<f", float(old_text))
        new = struct.pack("<f", float(new_text))
        if data[offset : offset + 4] != old:
            found = struct.unpack("<f", data[offset : offset + 4])[0]
            raise SystemExit(
                f"offset {offset}: expected {float(old_text)}, found {found}"
            )
        data[offset : offset + 4] = new
        print(f"patched offset {offset}: {old_text} -> {new_text}")
    Path(dst_path).write_bytes(data)


if __name__ == "__main__":
    main(*sys.argv[1:])
