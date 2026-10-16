"""Report translated rows whose renderer controls differ from the source."""

import csv
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

CONTROL_RE = re.compile(
    r"%[-+ #0]*\d*(?:\.\d+)?[sdif]|#[0-9]|\\[ben]|<[A-Za-z]+-?\d+>"
)


def normalize(text):
    return (text or "").replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")


def controls(text):
    return CONTROL_RE.findall(normalize(text))


def main():
    source_csv = sys.argv[1]
    with open(source_csv, "r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))

    problems = []
    for row in rows:
        ko = row.get("ko", "").strip()
        if not ko:
            continue
        # The English string is the runtime replacement target. Japanese is
        # only used for rows intentionally absent from the English release.
        reference = row.get("en", "") or row.get("jp", "")
        expected = controls(reference)
        actual = controls(ko)
        if expected != actual:
            problems.append((row.get("offset", ""), expected, actual, ko))

    for offset, expected, actual, ko in problems:
        print(f"{offset}: expected={expected!r} actual={actual!r}")
    print(f"checked={sum(1 for row in rows if row.get('ko', '').strip())} problems={len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
