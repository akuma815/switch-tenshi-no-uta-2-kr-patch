import os
import sys
import csv
import json

sys.path.insert(0, os.path.dirname(__file__))
from extract_strings import scan

uexp_path = sys.argv[1]
csv_path = sys.argv[2]
out_json = sys.argv[3]

items, _ = scan(uexp_path)
by_offset = {it["offset"]: it for it in items}

with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

replacements = []
skipped = 0
mismatched = 0
for row in rows:
    ko = (row.get("ko") or "").strip()
    off = (row.get("offset") or "").strip()
    if not ko or not off:
        skipped += 1
        continue
    off = int(off)
    it = by_offset.get(off)
    if it is None:
        mismatched += 1
        print(f"  no string at offset {off} (key {row['key']})")
        continue
    csv_en = row.get("en", "")
    # 엑셀 왕복에서 \r\n이 \n\n으로 변형될 수 있어 줄바꿈 연속을 하나로 접어 비교
    def norm(s):
        import re
        return re.sub(r"(\r\n|\r|\n)+", "\n", s)
    if norm(csv_en) != norm(it["text"]):
        mismatched += 1
        print(f"  text mismatch at offset {off} (key {row['key']}): csv len {len(csv_en)} vs scan len {len(it['text'])}")
        continue
    replacements.append({
        "offset": it["offset"],
        "old_encoding": it["encoding"],
        "old_length_field": it["length_field"],
        "old_text": it["text"],
        "new_text": ko,
    })

with open(out_json, "w", encoding="utf-8") as f:
    json.dump(replacements, f, ensure_ascii=False, indent=1)

print(f"replacements: {len(replacements)}, skipped(no ko/offset): {skipped}, mismatched: {mismatched}")
