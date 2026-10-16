import json
import csv
import sys


# The shipped localization table has one malformed enemy lookup key. Its JP
# slot ends in the CP932 minus glyph (817C), while the key contains '?' (3F),
# so Queen Viper resolves to an empty %s argument in battle messages.
TENSHI_KEY_FIXES = {
    "834E83438393836F834383703F": "834E83438393836F83438370817C",
}

# This event caption is immediately followed by the Ros Comaein location
# title in the same overlay slot. The original script omits the close marker,
# so the localized caption remains visible under the next title.
TENSHI_EVENT_CONTROL_SUFFIXES = {
    "1236328": r"\c",
}

def looks_like_hex_key(s):
    # Short source keys use upper-case bytes. Long keys can include lower-case
    # bytes, so only reject short English words such as "Dedeff".
    return (
        len(s) >= 4
        and all(c in "0123456789ABCDEFabcdef" for c in s)
        and (len(s) >= 8 or s == s.upper())
    )

def regen_tenshi_rows(strings_json):
    with open(strings_json, "r", encoding="utf-8") as f:
        items = json.load(f)
    rows = []
    i = 0
    n = len(items)
    while i < n:
        it = items[i]
        if it["encoding"] == "ascii" and looks_like_hex_key(it["text"]):
            key_item = it
            i += 1
            jp_item = None
            en_item = None
            if i < n and items[i]["encoding"] == "utf16":
                jp_item = items[i]
                i += 1
            if i < n and items[i]["encoding"] in ("ascii", "utf16"):
                nxt = items[i]
                if not (nxt["encoding"] == "ascii" and looks_like_hex_key(nxt["text"])):
                    en_item = nxt
                    i += 1
            rows.append({"key": key_item, "jp": jp_item, "en": en_item})
            continue
        i += 1
    return rows

def regen_visualscene_rows(strings_json):
    with open(strings_json, "r", encoding="utf-8") as f:
        items = json.load(f)

    def has_cjk(s):
        return any(
            0x3040 <= ord(c) <= 0x30FF
            or 0x3400 <= ord(c) <= 0x9FFF
            or 0xFF01 <= ord(c) <= 0xFF5E
            or 0xAC00 <= ord(c) <= 0xD7A3
            for c in s
        )

    rows = []
    i = 0
    n = len(items)
    while i < n - 1:
        a = items[i]
        b = items[i + 1]
        if has_cjk(a["text"]) and not has_cjk(b["text"]) and len(b["text"]) >= 1:
            rows.append({"jp": a, "en": b})
            i += 2
            continue
        i += 1
    return rows

def main():
    mode = sys.argv[1]  # "tenshi" or "visualscene"
    strings_json = sys.argv[2]
    ko_csv = sys.argv[3]
    out_json = sys.argv[4]

    if mode == "tenshi":
        regen = regen_tenshi_rows(strings_json)
    else:
        regen = regen_visualscene_rows(strings_json)

    with open(ko_csv, "r", encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.DictReader(f))

    if len(regen) != len(csv_rows):
        print(f"WARNING: row count mismatch: regen={len(regen)} csv={len(csv_rows)}")

    replacements = []
    mismatches = 0
    shared_source_slots = 0

    def norm(s):
        return s.replace("\r\n", "\n").replace("\r", "\n")

    # General dialogue sheets are user-maintained and can have rows removed
    # or sorted. Match them to the extracted source by the key FString offset
    # (the sheet's offset column), not by row order. key_hex can legitimately
    # repeat for identical battle messages at different locations.
    if mode == "tenshi":
        regen_by_offset = {str(r["key"]["offset"]): r for r in regen}
        pairs = []
        for c in csv_rows:
            r = regen_by_offset.get(c.get("offset", ""))
            if r is None or r["key"]["text"] != c.get("key_hex", ""):
                mismatches += 1
                continue
            pairs.append((r, c))

        for r in regen:
            old_key = r["key"]["text"]
            new_key = TENSHI_KEY_FIXES.get(old_key)
            if new_key:
                replacements.append({
                    "offset": r["key"]["offset"],
                    "old_encoding": r["key"]["encoding"],
                    "old_length_field": r["key"]["length_field"],
                    "old_text": old_key,
                    "new_text": new_key,
                    "new_encoding": "ascii",
                })
    else:
        pairs = zip(regen, csv_rows)

    for r, c in pairs:
        en_item = r.get("en")
        ko = c.get("ko", "").strip()
        if not ko:
            continue
        if mode == "tenshi":
            suffix = TENSHI_EVENT_CONTROL_SUFFIXES.get(c.get("offset", ""))
            if suffix and not ko.endswith(suffix):
                ko += suffix
        csv_en = c.get("en", "")
        if en_item is None:
            # Some map labels are already English in the common JP slot and
            # therefore have no separate English FString. Only use that slot
            # when the sheet's non-empty English value matches it exactly.
            jp_item = r.get("jp")
            if jp_item is None or not csv_en or norm(csv_en) != norm(jp_item["text"]):
                mismatches += 1
                continue
            source_item = jp_item
            shared_source_slots += 1
        else:
            source_item = en_item
        # sanity check text matches (allow the csv's en field to match)
        # 엑셀 왕복에서 \r\n으로 변형될 수 있으므로 줄바꿈 정규화 후 비교
        if norm(csv_en) != norm(source_item["text"]):
            mismatches += 1
            continue
        replacements.append({
            "offset": source_item["offset"],
            "old_encoding": source_item["encoding"],
            "old_length_field": source_item["length_field"],
            "old_text": source_item["text"],
            "new_text": ko,
        })

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(replacements, f, ensure_ascii=False, indent=1)

    print(f"regen rows: {len(regen)}, csv rows: {len(csv_rows)}, mismatches: {mismatches}")
    if shared_source_slots:
        print(f"shared JP/EN source slots: {shared_source_slots}")
    print(f"replacements built: {len(replacements)}")

if __name__ == "__main__":
    main()
