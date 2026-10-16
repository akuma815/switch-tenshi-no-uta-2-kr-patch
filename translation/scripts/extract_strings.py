import struct
import sys
import json
import csv

def is_probably_text_utf16(chars):
    # chars: python str
    if not chars:
        return False
    bad = 0
    for ch in chars:
        cp = ord(ch)
        if ch in "\t\r\n":
            continue
        if cp < 0x20:
            return False
        # printable ascii, latin supplement, CJK, hangul, common punctuation/symbols
        if not (0x20 <= cp <= 0x7E or 0xA0 <= cp <= 0x24FF or 0x2E80 <= cp <= 0xD7FF or 0xFF00 <= cp <= 0xFFEF):
            bad += 1
    return bad <= max(1, len(chars) // 20)

def is_probably_text_ascii(chars):
    if not chars:
        return False
    for ch in chars:
        cp = ord(ch)
        if ch in "\t\r\n":
            continue
        if cp < 0x20 or cp > 0x7E:
            return False
    return True

def scan(path):
    with open(path, "rb") as f:
        data = f.read()
    n = len(data)
    results = []
    i = 0
    while i + 4 <= n:
        (num,) = struct.unpack_from("<i", data, i)
        if num == 0:
            i += 1
            continue
        if 0 < num <= 20000:
            # ascii/utf8, num includes null terminator
            start = i + 4
            end = start + num
            if end <= n and data[end - 1] == 0:
                raw = data[start:end - 1]
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = None
                if text is not None and is_probably_text_ascii(text) and len(text) >= 2:
                    results.append({
                        "offset": i,
                        "encoding": "ascii",
                        "length_field": num,
                        "text": text,
                    })
                    i = end
                    continue
        elif -20000 <= num < 0:
            count = -num
            start = i + 4
            end = start + count * 2
            if end <= n:
                raw = data[start:end]
                if len(raw) >= 2 and raw[-2] == 0 and raw[-1] == 0:
                    try:
                        text = raw[:-2].decode("utf-16-le")
                    except UnicodeDecodeError:
                        text = None
                    if text is not None and is_probably_text_utf16(text) and len(text) >= 1:
                        results.append({
                            "offset": i,
                            "encoding": "utf16",
                            "length_field": num,
                            "text": text,
                        })
                        i = end
                        continue
        i += 1
    return results, n

if __name__ == "__main__":
    in_path = sys.argv[1]
    out_json = sys.argv[2]
    out_csv = sys.argv[3]
    results, n = scan(in_path)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["offset", "encoding", "length_field", "text"])
        for r in results:
            w.writerow([r["offset"], r["encoding"], r["length_field"], r["text"]])
    print(f"file size: {n} bytes")
    print(f"strings found: {len(results)}")
    enc_counts = {}
    for r in results:
        enc_counts[r["encoding"]] = enc_counts.get(r["encoding"], 0) + 1
    print("by encoding:", enc_counts)
