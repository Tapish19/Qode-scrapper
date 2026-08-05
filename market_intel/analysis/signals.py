from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow.dataset as ds

from market_intel.analysis.features import extract_text_features, tweet_signal


@dataclass(slots=True)
class WindowStats:
    count: int = 0
    weight_sum: float = 0.0
    weighted_signal_sum: float = 0.0
    weighted_signal_sq_sum: float = 0.0
    engagement_sum: int = 0
    risk_sum: float = 0.0
    bullish_count: int = 0
    bearish_count: int = 0
    neutral_count: int = 0
    usernames: set[str] | None = None

    def __post_init__(self) -> None:
        if self.usernames is None:
            self.usernames = set()


def _floor_window(timestamp: datetime, minutes: int) -> datetime:
    minute = timestamp.minute - timestamp.minute % minutes
    return timestamp.replace(minute=minute, second=0, microsecond=0)


def _hashtags_to_market(hashtags: list[str] | None, query_tag: str | None) -> str:
    tags = {x.lower() for x in (hashtags or [])}
    if query_tag:
        tags.add(query_tag.lower())
    for candidate in ("banknifty", "nifty50", "sensex", "intraday"):
        if candidate in tags:
            return candidate
    return "other"


def analyze_dataset(
    dataset_path: Path,
    output_dir: Path,
    *,
    window_minutes: int = 15,
    batch_size: int = 2_000,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = ds.dataset(str(dataset_path), format="parquet", partitioning="hive")
    columns = [
        "timestamp", "normalized_content", "engagement_total", "view_count",
        "username", "hashtags", "query_tag",
    ]
    scanner = dataset.scanner(columns=columns, batch_size=batch_size)

    windows: dict[tuple[datetime, str], WindowStats] = defaultdict(WindowStats)
    total_rows = 0
    language_counts: dict[str, int] = defaultdict(int)
    now = datetime.now(timezone.utc)

    language_scanner = dataset.scanner(columns=["language_hint"], batch_size=batch_size)
    for batch in language_scanner.to_batches():
        for value in batch.column(0).to_pylist():
            language_counts[value or "unknown"] += 1

    for batch in scanner.to_batches():
        for row in batch.to_pylist():
            total_rows += 1
            timestamp = row["timestamp"].astimezone(timezone.utc)
            features = extract_text_features(row["normalized_content"] or "")
            signal, weight = tweet_signal(
                polarity=features.polarity,
                engagement_total=row["engagement_total"] or 0,
                view_count=row["view_count"] or 0,
                timestamp=timestamp,
                manipulation_risk=features.manipulation_risk,
                now=now,
            )
            market = _hashtags_to_market(row["hashtags"], row["query_tag"])
            key = (_floor_window(timestamp, window_minutes), market)
            stats = windows[key]
            stats.count += 1
            stats.weight_sum += weight
            stats.weighted_signal_sum += weight * signal
            stats.weighted_signal_sq_sum += weight * signal * signal
            stats.engagement_sum += row["engagement_total"] or 0
            stats.risk_sum += features.manipulation_risk
            stats.usernames.add(row["username"] or "unknown")
            if signal > 0.05:
                stats.bullish_count += 1
            elif signal < -0.05:
                stats.bearish_count += 1
            else:
                stats.neutral_count += 1

    rows: list[dict[str, Any]] = []
    for (window_start, market), stats in sorted(windows.items()):
        mean = stats.weighted_signal_sum / stats.weight_sum if stats.weight_sum else 0.0
        second_moment = (
            stats.weighted_signal_sq_sum / stats.weight_sum if stats.weight_sum else 0.0
        )
        variance = max(0.0, second_moment - mean * mean)
        effective_n = max(1.0, min(float(stats.count), stats.weight_sum))
        standard_error = math.sqrt(variance / effective_n)
        margin = 1.96 * standard_error
        diversity = len(stats.usernames) / max(1, stats.count)
        confidence = min(
            1.0,
            0.45 * min(1.0, stats.count / 40)
            + 0.35 * diversity
            + 0.20 * max(0.0, 1.0 - margin),
        )
        rows.append(
            {
                "window_start": window_start.isoformat(),
                "market": market,
                "tweet_count": stats.count,
                "unique_authors": len(stats.usernames),
                "engagement_total": stats.engagement_sum,
                "bullish_count": stats.bullish_count,
                "bearish_count": stats.bearish_count,
                "neutral_count": stats.neutral_count,
                "composite_signal": round(mean, 6),
                "ci95_lower": round(max(-1.0, mean - margin), 6),
                "ci95_upper": round(min(1.0, mean + margin), 6),
                "confidence": round(confidence, 6),
                "manipulation_risk_mean": round(stats.risk_sum / stats.count, 6),
            }
        )

    csv_path = output_dir / "signals_15m.csv"
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    else:
        csv_path.write_text("", encoding="utf-8")

    overall = _overall_summary(rows, total_rows, language_counts)
    (output_dir / "summary.json").write_text(
        json.dumps(overall, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return overall


def _overall_summary(
    rows: list[dict[str, Any]],
    total_rows: int,
    language_counts: dict[str, int],
) -> dict[str, Any]:
    if not rows:
        return {"tweet_count": total_rows, "status": "no_data", "language_counts": language_counts}
    weighted_sum = sum(r["composite_signal"] * r["tweet_count"] for r in rows)
    count_sum = sum(r["tweet_count"] for r in rows)
    overall_signal = weighted_sum / count_sum if count_sum else 0.0
    label = "bullish" if overall_signal > 0.08 else "bearish" if overall_signal < -0.08 else "neutral"
    return {
        "tweet_count": total_rows,
        "window_count": len(rows),
        "overall_signal": round(overall_signal, 6),
        "overall_label": label,
        "language_counts": dict(language_counts),
        "methodology": {
            "text_features": "finance lexicon + negation + manipulation-risk discount",
            "weighting": "recency decay + log engagement + log reach",
            "confidence_interval": "normal approximation over weighted window variance",
            "disclaimer": "Research signal only; not financial advice or an execution strategy.",
        },
    }
