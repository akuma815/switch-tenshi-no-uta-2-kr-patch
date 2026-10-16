"""Find identical source strings that have multiple Korean translations.

Usage: python find_inconsistent_translations.py <master CSV> <report CSV>
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path


def normalize(text):
    return (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def main():
    source_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    with source_path.open(encoding="utf-8-sig", newline="") as source_file:
        rows = list(csv.DictReader(source_file))

    report_rows = []
    group_number = 0
    group_counts = {}
    for source_field in ("jp", "en"):
        groups = defaultdict(list)
        for row in rows:
            source_text = normalize(row.get(source_field))
            korean = normalize(row.get("ko"))
            if source_text and korean:
                groups[source_text].append(row)

        conflicts = []
        for source_text, occurrences in groups.items():
            variants = defaultdict(list)
            for row in occurrences:
                variants[normalize(row.get("ko"))].append(row)
            if len(variants) > 1:
                conflicts.append((source_text, occurrences, variants))

        conflicts.sort(key=lambda item: ("\n" in item[0], len(item[0]), item[0]))
        group_counts[source_field] = len(conflicts)
        for source_text, occurrences, variants in conflicts:
            group_number += 1
            group_id = f"G{group_number:03d}"
            term_like = "Y" if "\n" not in source_text and len(source_text) <= 30 else "N"
            sorted_variants = sorted(
                variants.items(),
                key=lambda item: (-len(item[1]), item[0]),
            )
            for variant_number, (korean, variant_rows) in enumerate(sorted_variants, 1):
                report_rows.append({
                    "group_id": group_id,
                    "source_field": source_field,
                    "term_like": term_like,
                    "source_text": source_text,
                    "translation_count": len(variants),
                    "occurrence_count": len(occurrences),
                    "variant": variant_number,
                    "ko": korean,
                    "offsets": " | ".join(row.get("offset", "") for row in variant_rows),
                    "jp_examples": " | ".join(dict.fromkeys(normalize(row.get("jp")) for row in variant_rows)),
                    "en_examples": " | ".join(dict.fromkeys(normalize(row.get("en")) for row in variant_rows)),
                })

    columns = [
        "group_id",
        "source_field",
        "term_like",
        "source_text",
        "translation_count",
        "occurrence_count",
        "variant",
        "ko",
        "offsets",
        "jp_examples",
        "en_examples",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(report_rows)

    print(
        f"conflict groups: jp={group_counts['jp']}, en={group_counts['en']}, "
        f"report rows={len(report_rows)}"
    )
    print(f"written: {output_path}")


if __name__ == "__main__":
    main()
