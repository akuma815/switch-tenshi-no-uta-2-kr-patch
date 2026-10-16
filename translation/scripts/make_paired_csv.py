"""2편(tenshi2) 번역용 페어링 CSV 생성 (초기 1회용)

사용법: python make_paired_csv.py
- work\tenshi2_strings.json / vs2_strings.json (extract_strings.py 결과) 필요
- work\src\Emulator_Tenshinouta\Content (retoc to-legacy 추출본) 필요
- 결과: 백업_csv\*.csv (ko 컬럼은 비움)

1편 백업_csv와 동일한 컬럼 구조:
  tenshi:      offset(key), key_hex, jp, en, ko
  visualscene: offset(jp), jp, en, ko
  ui_menu:     table, index, jp, en, ko
  outgameinfo: key, offset(값), en, ko
"""
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from extract_strings import scan

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, "work")
CONTENT = os.path.join(WORK, "src", "Emulator_Tenshinouta", "Content")
OUT = os.path.join(BASE, "백업_csv")
os.makedirs(OUT, exist_ok=True)


def write_csv(path, fieldnames, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"{os.path.basename(path)}: {len(rows)} rows")


def looks_like_hex_key(s):
    return len(s) >= 4 and all(c in "0123456789ABCDEFabcdef" for c in s)


def make_tenshi():
    with open(os.path.join(WORK, "tenshi2_strings.json"), encoding="utf-8") as f:
        items = json.load(f)
    rows = []
    i, n = 0, len(items)
    while i < n:
        it = items[i]
        if it["encoding"] == "ascii" and looks_like_hex_key(it["text"]):
            key = it
            i += 1
            jp = en = None
            if i < n and items[i]["encoding"] == "utf16":
                jp = items[i]
                i += 1
            if i < n:
                nxt = items[i]
                if not (nxt["encoding"] == "ascii" and looks_like_hex_key(nxt["text"])):
                    en = nxt
                    i += 1
            rows.append({
                "offset": key["offset"],
                "key_hex": key["text"],
                "jp": jp["text"] if jp else "",
                "en": en["text"] if en else "",
                "ko": "",
            })
            continue
        i += 1
    write_csv(os.path.join(OUT, "tenshi2_text_en_paired.csv"),
              ["offset", "key_hex", "jp", "en", "ko"], rows)


def has_cjk(s):
    # U+3000 is an ideographic space. It appears at the start of some English
    # credit lines, so it must not by itself classify the line as Japanese.
    return any(
        0x3040 <= ord(c) <= 0x30FF
        or 0x3400 <= ord(c) <= 0x9FFF
        or 0xFF01 <= ord(c) <= 0xFF5E
        or 0xAC00 <= ord(c) <= 0xD7A3
        for c in s
    )


def make_visualscene():
    with open(os.path.join(WORK, "vs2_strings.json"), encoding="utf-8") as f:
        items = json.load(f)
    rows = []
    i, n = 0, len(items)
    while i < n - 1:
        a, b = items[i], items[i + 1]
        if has_cjk(a["text"]) and not has_cjk(b["text"]) and len(b["text"]) >= 1:
            rows.append({"offset": a["offset"], "jp": a["text"], "en": b["text"], "ko": ""})
            i += 2
            continue
        i += 1
    write_csv(os.path.join(OUT, "visualscene2_paired.csv"),
              ["offset", "jp", "en", "ko"], rows)


# L10N en 테이블과 base(비 L10N) 대응 파일. jp 컬럼은 base 파일 같은 인덱스에서.
UI_TABLES = [
    ("DT_BootView", "Common/DT_BootView.uexp"),
    ("DT_Game2_GameInfo", "Game_2/DT_Game2_GameInfo.uexp"),
    ("DT_Game1_HomeMenuSelectInfo", "Game_1/DT_Game1_HomeMenuSelectInfo.uexp"),
    ("DT_Game2_SoundInfo", "Game_2/DT_Game2_SoundInfo.uexp"),
    ("DT_Game2_VisualInfo", "Game_2/DT_Game2_VisualInfo.uexp"),
    ("DT_Game1_SoundInfo", "Game_1/DT_Game1_SoundInfo.uexp"),
    ("DT_Game1_VisualInfo", "Game_1/DT_Game1_VisualInfo.uexp"),
]


def make_ui_menu():
    en_root = os.path.join(CONTENT, "L10N", "en", "Ogix", "Data", "DT")
    base_root = os.path.join(CONTENT, "Ogix", "Data", "DT")
    rows = []
    for table, rel in UI_TABLES:
        en_path = os.path.join(en_root, rel)
        if not os.path.exists(en_path):
            print(f"  skip (없음): {rel}")
            continue
        en_items, _ = scan(en_path)
        base_path = os.path.join(base_root, rel)
        base_items = scan(base_path)[0] if os.path.exists(base_path) else []
        jp_by_idx = {}
        if len(base_items) == len(en_items):
            jp_by_idx = {i: it["text"] for i, it in enumerate(base_items)}
        for i, it in enumerate(en_items):
            rows.append({
                "table": table,
                "index": i,
                "jp": jp_by_idx.get(i, ""),
                "en": it["text"],
                "ko": "",
            })
    write_csv(os.path.join(OUT, "ui_menu_text2_paired.csv"),
              ["table", "index", "jp", "en", "ko"], rows)


def make_outgameinfo():
    path = os.path.join(CONTENT, "Localization", "DataTable_Game1", "ST_OutGameInfo_Game1.uexp")
    items, _ = scan(path)
    rows = []
    i, n = 0, len(items)
    while i < n:
        it = items[i]
        if it["encoding"] == "ascii" and re.fullmatch(r"Str\d+", it["text"]):
            key = it["text"]
            if i + 1 < n and not re.fullmatch(r"Str\d+", items[i + 1]["text"]):
                val = items[i + 1]
                rows.append({"key": key, "offset": val["offset"], "en": val["text"], "ko": ""})
                i += 2
                continue
        i += 1
    write_csv(os.path.join(OUT, "outgameinfo2_paired.csv"),
              ["key", "offset", "en", "ko"], rows)


if __name__ == "__main__":
    make_tenshi()
    make_visualscene()
    make_ui_menu()
    make_outgameinfo()
