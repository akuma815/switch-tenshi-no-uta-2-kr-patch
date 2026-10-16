"""Find Korean rows copied or shifted onto unrelated source strings."""

import csv
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import re
import sys


CONTROL_RE = re.compile(r"#[0-9]|\\[a-z]|<[A-Za-z]+-?\d+>|%[-+ #0-9.]*[A-Za-z]")


def normalize(text):
    text = CONTROL_RE.sub(" ", text or "").replace("\\n", " ")
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", text).lower()


def main():
    source_csv, output_csv = sys.argv[1:3]
    minimum_similarity = float(sys.argv[3]) if len(sys.argv) > 3 else 0.68
    with open(source_csv, "r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))

    ko_texts = [normalize(row.get("ko", "")) for row in rows]
    en_texts = [normalize(row.get("en", "")) for row in rows]
    grams = defaultdict(set)
    for index, text in enumerate(ko_texts):
        if len(text) < 12:
            continue
        for pos in range(len(text) - 3):
            grams[text[pos : pos + 4]].add(index)

    results = []
    seen = set()
    for index, text in enumerate(ko_texts):
        if len(text) < 12:
            continue
        overlaps = Counter()
        for pos in range(len(text) - 3):
            for other in grams[text[pos : pos + 4]]:
                if other != index:
                    overlaps[other] += 1
        for other, _ in overlaps.most_common(8):
            pair = tuple(sorted((index, other)))
            if pair in seen:
                continue
            seen.add(pair)
            ko_similarity = SequenceMatcher(None, text, ko_texts[other]).ratio()
            if ko_similarity < minimum_similarity:
                continue
            en_similarity = SequenceMatcher(None, en_texts[index], en_texts[other]).ratio()
            if en_similarity >= 0.38:
                continue
            results.append(
                {
                    "offset_a": rows[index]["offset"],
                    "offset_b": rows[other]["offset"],
                    "ko_similarity": f"{ko_similarity:.3f}",
                    "en_similarity": f"{en_similarity:.3f}",
                    "en_a": rows[index]["en"],
                    "ko_a": rows[index]["ko"],
                    "en_b": rows[other]["en"],
                    "ko_b": rows[other]["ko"],
                }
            )

    results.sort(key=lambda row: float(row["ko_similarity"]), reverse=True)
    fields = list(results[0]) if results else ["offset_a", "offset_b"]
    with open(output_csv, "w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    print(f"near-duplicate candidates: {len(results)}")


if __name__ == "__main__":
    main()
