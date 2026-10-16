"""Keep Korean dialogue line breaks aligned with the source layout."""

import csv
import re
import sys


CODE_RE = re.compile(r"#\d")
LAYOUT_TAG_RE = re.compile(r"<[A-Za-z]+-?\d+>")


def char_width(ch):
    cp = ord(ch)
    if cp < 0x2000 or 0xFF61 <= cp <= 0xFF9F:
        return 0.5
    return 1.0


def text_width(text):
    return sum(char_width(ch) for ch in CODE_RE.sub("", text))


def normalize_newlines(text):
    return text.replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")


def split_to_source_layout(ko, jp):
    """Preserve matching translation layout; otherwise use the source line count."""
    ko = normalize_newlines(ko)

    # <X124>, <Y40> are renderer layout commands, not visible text.  A
    # line-count reflow can split a tag (for example <Y\n40>) and makes the
    # renderer ignore every following placement command.  Keep translator
    # supplied breaks intact for these coordinate-driven status layouts.
    if LAYOUT_TAG_RE.search(ko):
        return ko

    # Dialogue name/style transitions (for example "#5Name:\n#1Text")
    # define separate renderer runs. Reflowing them to the Japanese line
    # count can split the first Korean word immediately after #1 or move the
    # intended dialogue break. Keep the translator's layout intact.
    if re.search(r"\n#\d", ko):
        return ko

    # Level-up result strings use \b as a page/control marker followed by
    # optional runtime %s messages.  Their source concatenates the suffixes,
    # but Korean needs explicit line breaks before the result messages.
    if r"\b" in ko:
        return ko

    jp_lines = normalize_newlines(jp).split("\n")
    target_count = len(jp_lines)

    if ko.count("\n") + 1 == target_count:
        return ko

    if target_count == 1:
        return " ".join(part.strip() for part in ko.split("\n") if part.strip())

    # Only mismatched rows are reflowed. Source line widths determine the
    # relative Korean break positions, with a nearby space preferred.
    text = " ".join(part.strip() for part in ko.split("\n") if part.strip())
    if not text:
        return ko

    source_widths = [max(text_width(line), 1.0) for line in jp_lines]
    source_total = sum(source_widths)
    target_total = text_width(text)
    result = []
    start = 0
    consumed = 0.0

    for line_index in range(target_count - 1):
        target = (sum(source_widths[: line_index + 1]) / source_total) * target_total
        index = start
        while index < len(text) and consumed < target:
            consumed += char_width(text[index])
            index += 1

        remaining_lines = target_count - line_index - 1
        index = min(max(index, start + 1), len(text) - remaining_lines)
        space = text.rfind(" ", start, index + 1)
        if space > start and index - space <= max(4, (index - start) // 3):
            index = space

        result.append(text[start:index].strip())
        start = index
        while start < len(text) and text[start] == " ":
            start += 1

    result.append(text[start:].strip())
    return "\n".join(result)


def main():
    in_csv, out_csv = sys.argv[1:3]
    with open(in_csv, "r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
        fieldnames = list(rows[0].keys())

    layout_fixed = 0
    over_three = 0
    for row in rows:
        ko = normalize_newlines(row.get("ko") or "")
        if not ko.strip():
            continue
        new_ko = split_to_source_layout(ko, row.get("jp") or "")
        if new_ko != ko:
            layout_fixed += 1
        if new_ko.count("\n") + 1 > 3:
            over_three += 1
        row["ko"] = new_ko.replace("\n", "\\n")

    with open(out_csv, "w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    translated = sum(1 for row in rows if (row.get("ko") or "").strip())
    print(
        f"rows with ko: {translated}, source-layout fixes: {layout_fixed}, "
        f"entries exceeding 3 lines: {over_three}"
    )


if __name__ == "__main__":
    main()
