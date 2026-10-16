import struct
import sys
from pathlib import Path


def patch_font_size(src_uexp, dst_uexp, old_size, new_size, expected_count):
    data = bytearray(Path(src_uexp).read_bytes())
    old = struct.pack("<f", float(old_size))
    new = struct.pack("<f", float(new_size))
    count = data.count(old)
    if count != int(expected_count):
        raise SystemExit(f"expected {expected_count} font-size values, found {count}")
    data = data.replace(old, new)
    Path(dst_uexp).write_bytes(data)
    print(f"patched DT_RichTextFormat font size: {old_size} -> {new_size} ({count} values)")


if __name__ == "__main__":
    patch_font_size(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
