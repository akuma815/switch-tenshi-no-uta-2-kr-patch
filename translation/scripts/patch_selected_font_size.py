"""Patch selected little-endian float occurrences in a UEXP file."""

import struct
import sys
from pathlib import Path


def main() -> int:
    path = Path(sys.argv[1])
    old = struct.pack("<f", float(sys.argv[2]))
    new = struct.pack("<f", float(sys.argv[3]))
    indexes = {int(value) for value in sys.argv[4].split(",")}
    data = bytearray(path.read_bytes())
    positions = []
    start = 0
    while True:
        pos = data.find(old, start)
        if pos < 0:
            break
        positions.append(pos)
        start = pos + len(old)
    for index in indexes:
        if index < 1 or index > len(positions):
            raise SystemExit(f"float occurrence {index} is outside 1..{len(positions)}")
        pos = positions[index - 1]
        data[pos : pos + len(new)] = new
    path.write_bytes(data)
    print(f"patched {path.name}: occurrences {sorted(indexes)} {sys.argv[2]} -> {sys.argv[3]}")


if __name__ == "__main__":
    main()
