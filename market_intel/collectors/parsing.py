from __future__ import annotations

import re

_COUNT_RE = re.compile(r"([\d,.]+)\s*([KkMm]?)")


def parse_compact_count(value: str | None) -> int:
    """Convert UI counts such as 2.5K or 1.2M into integers."""
    if not value:
        return 0
    match = _COUNT_RE.search(value.replace(" ", " "))
    if not match:
        return 0
    number = float(match.group(1).replace(",", ""))
    suffix = match.group(2).lower()
    multiplier = 1_000 if suffix == "k" else 1_000_000 if suffix == "m" else 1
    return int(number * multiplier)
