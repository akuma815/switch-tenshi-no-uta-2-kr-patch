import struct
import sys
import json

def encode_replacement(text, encoding="utf16"):
    if encoding == "ascii":
        data = text.encode("ascii") + b"\x00"
        return struct.pack("<i", len(data)) + data

    # Korean values use UE FString UTF-16LE: negative length includes the null.
    data = text.encode("utf-16-le") + b"\x00\x00"
    count = len(data) // 2
    return struct.pack("<i", -count) + data

def apply(uexp_path, replacements, out_path):
    with open(uexp_path, "rb") as f:
        data = f.read()

    replacements = sorted(replacements, key=lambda r: r["offset"])

    out = bytearray()
    cursor = 0
    for r in replacements:
        off = r["offset"]
        enc = r["old_encoding"]
        length_field = r["old_length_field"]
        if enc == "ascii":
            old_total = 4 + length_field
        else:
            old_total = 4 + (-length_field) * 2
        if off < cursor:
            raise ValueError(f"overlapping replacement at offset {off} (cursor={cursor})")
        out += data[cursor:off]
        out += encode_replacement(r["new_text"], r.get("new_encoding", "utf16"))
        cursor = off + old_total
    out += data[cursor:]

    with open(out_path, "wb") as f:
        f.write(bytes(out))

    return len(data), len(out)

if __name__ == "__main__":
    uexp_path = sys.argv[1]
    repl_json = sys.argv[2]
    out_path = sys.argv[3]
    file_filter = sys.argv[4] if len(sys.argv) > 4 else None

    with open(repl_json, "r", encoding="utf-8") as f:
        all_repl = json.load(f)

    if file_filter:
        repl = [r for r in all_repl if r.get("file") == file_filter]
    else:
        repl = all_repl

    old_len, new_len = apply(uexp_path, repl, out_path)
    print(f"applied {len(repl)} replacements: {old_len} bytes -> {new_len} bytes (delta {new_len - old_len})")
