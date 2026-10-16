import os
import sys
import csv
import json

sys.path.insert(0, os.path.dirname(__file__))
from extract_strings import scan

LEGACY_DT = sys.argv[1]
CSV_PATH = sys.argv[2]
OUT_JSON = sys.argv[3]

BASE_ROOT = os.path.join(LEGACY_DT, "Emulator_Tenshinouta", "Content", "Ogix", "Data", "DT")
EN_ROOT = os.path.join(LEGACY_DT, "Emulator_Tenshinouta", "Content", "L10N", "en", "Ogix", "Data", "DT")

# table -> (source file relative to EN_ROOT, encoding filter) used when building ui_menu_text_paired.csv "en" column
EN_SOURCES = {
    "DT_BootView": "Common/DT_BootView.uexp",
    "DT_Game1_GameInfo": "Game_1/DT_Game1_GameInfo.uexp",
    "DT_Game1_HomeMenuSelectInfo": "Game_1/DT_Game1_HomeMenuSelectInfo.uexp",
    "DT_Game1_SoundInfo": "Game_1/DT_Game1_SoundInfo.uexp",
    "DT_Game1_VisualInfo": "Game_1/DT_Game1_VisualInfo.uexp",
}

# also patch these base (non-L10N) files where content is a literal duplicate (utf16-encoded) of the same text
BASE_DUPLICATE_SOURCES = {
    "DT_BootView": "Common/DT_BootView.uexp",
}

with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
    csv_rows = list(csv.DictReader(f))

by_table = {}
for row in csv_rows:
    by_table.setdefault(row["table"], []).append(row)

replacements = []
mismatches = 0

for table, rel in EN_SOURCES.items():
    path = os.path.join(EN_ROOT, rel)
    items, _ = scan(path)
    rows = by_table.get(table, [])
    for row in rows:
        idx = int(row["index"])
        ko = row.get("ko", "").strip()
        if not ko:
            continue
        if idx >= len(items):
            mismatches += 1
            continue
        it = items[idx]
        def norm(s):
            return s.replace("\r\n", "\n").replace("\r", "\n")
        if norm(it["text"]) != norm(row.get("en", "")):
            mismatches += 1
            print(f"  mismatch: table={table} index={idx}")
            continue
        replacements.append({
            "file": os.path.join("L10N", "en", "Ogix", "Data", "DT", rel).replace("\\", "/"),
            "offset": it["offset"],
            "old_encoding": it["encoding"],
            "old_length_field": it["length_field"],
            "old_text": it["text"],
            "new_text": ko.replace("\r\n", "\n").replace("\r", "\n"),
        })

for table, rel in BASE_DUPLICATE_SOURCES.items():
    path = os.path.join(BASE_ROOT, rel)
    items, _ = scan(path)
    utf16_items = [it for it in items if it["encoding"] == "utf16"]
    rows = by_table.get(table, [])
    for row in rows:
        idx = int(row["index"])
        ko = row.get("ko", "").strip()
        if not ko:
            continue
        if idx >= len(utf16_items):
            mismatches += 1
            continue
        it = utf16_items[idx]
        # base file holds the JP-duplicate text; just confirm it's non-empty
        replacements.append({
            "file": os.path.join("Ogix", "Data", "DT", rel).replace("\\", "/"),
            "offset": it["offset"],
            "old_encoding": it["encoding"],
            "old_length_field": it["length_field"],
            "old_text": it["text"],
            "new_text": ko,
        })

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(replacements, f, ensure_ascii=False, indent=1)

print(f"replacements built: {len(replacements)}, mismatches: {mismatches}")
by_file = {}
for r in replacements:
    by_file.setdefault(r["file"], 0)
    by_file[r["file"]] += 1
for k, v in by_file.items():
    print(f"  {k}: {v}")
