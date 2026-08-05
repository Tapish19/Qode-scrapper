"""Generate the checked-in synthetic CSV preview without requiring PyArrow.

The production CLI writes Parquet. This helper exists only so reviewers can inspect
sample records and analysis outputs immediately after cloning the repository.
"""
from __future__ import annotations

import csv
import json
import math
import random
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from market_intel.analysis.features import extract_text_features, tweet_signal
from market_intel.analysis.visualize import plot_signal_series
from market_intel.processing.normalize import normalize_text, text_for_analysis

SAMPLE_PATH = ROOT / "data/sample/tweets_preview.csv"
OUTPUT_DIR = ROOT / "data/output"
END_TIME = datetime(2026, 8, 4, 8, 28, tzinfo=timezone.utc)

BULLISH = [
    "#NIFTY50 breakout above support, looking bullish with target 24500",
    "Bank Nifty में तेजी, buyers are strong today #banknifty",
    "Accumulating quality stocks on dips. Market looks strong #sensex",
    "#intraday long setup confirmed, upside possible after consolidation",
]
BEARISH = [
    "#NIFTY50 breakdown below support, bearish pressure increasing",
    "Bank Nifty में गिरावट, sell on rise setup #banknifty",
    "Weak breadth and downside risk in #sensex today",
    "#intraday short setup; avoid aggressive buying in this volatility",
]
NEUTRAL = [
    "#NIFTY50 trading in a range; waiting for confirmation",
    "Watching option chain and market breadth before taking a trade #banknifty",
    "No clear setup in #sensex yet, risk management is important",
    "#intraday levels posted for educational discussion only",
]
RISKY = [
    "SURE SHOT multibagger guaranteed double money #intraday",
    "Operator stock upper circuit fixed target 100% #sensex",
]


def floor_window(value: datetime, minutes: int = 15) -> datetime:
    return value.replace(minute=value.minute - value.minute % minutes, second=0, microsecond=0)


def main() -> None:
    rng = random.Random(42)
    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    templates = BULLISH * 4 + BEARISH * 3 + NEUTRAL * 3 + RISKY
    tags = ["nifty50", "sensex", "intraday", "banknifty"]
    rows: list[dict[str, object]] = []

    for index in range(2_500):
        content = rng.choice(templates)
        tag = next((tag for tag in tags if f"#{tag}" in content.lower()), rng.choice(tags))
        timestamp = END_TIME - timedelta(seconds=rng.randint(0, 24 * 3600 - 1))
        row = {
            "tweet_id": f"sample-{index:07d}",
            "username": f"sample_trader_{rng.randint(1, 420)}",
            "timestamp": timestamp.isoformat(),
            "content": normalize_text(content),
            "normalized_content": text_for_analysis(content),
            "reply_count": rng.randint(0, 30),
            "repost_count": rng.randint(0, 80),
            "like_count": rng.randint(0, 500),
            "view_count": rng.randint(50, 80_000),
            "bookmark_count": rng.randint(0, 20),
            "mentions": "nseindia" if rng.random() < 0.08 else "",
            "hashtags": tag,
            "query_tag": tag,
            "synthetic": True,
        }
        row["engagement_total"] = (
            int(row["reply_count"])
            + int(row["repost_count"])
            + int(row["like_count"])
            + int(row["bookmark_count"])
        )
        rows.append(row)

    with SAMPLE_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    stats: dict[tuple[datetime, str], dict[str, object]] = defaultdict(
        lambda: {
            "count": 0,
            "weight": 0.0,
            "sum": 0.0,
            "sq": 0.0,
            "engagement": 0,
            "risk": 0.0,
            "bullish": 0,
            "bearish": 0,
            "neutral": 0,
            "authors": set(),
        }
    )
    for row in rows:
        timestamp = datetime.fromisoformat(str(row["timestamp"]))
        features = extract_text_features(str(row["normalized_content"]))
        signal, weight = tweet_signal(
            polarity=features.polarity,
            engagement_total=int(row["engagement_total"]),
            view_count=int(row["view_count"]),
            timestamp=timestamp,
            manipulation_risk=features.manipulation_risk,
            now=END_TIME,
        )
        bucket = stats[(floor_window(timestamp), str(row["query_tag"]))]
        bucket["count"] = int(bucket["count"]) + 1
        bucket["weight"] = float(bucket["weight"]) + weight
        bucket["sum"] = float(bucket["sum"]) + weight * signal
        bucket["sq"] = float(bucket["sq"]) + weight * signal * signal
        bucket["engagement"] = int(bucket["engagement"]) + int(row["engagement_total"])
        bucket["risk"] = float(bucket["risk"]) + features.manipulation_risk
        cast_authors = bucket["authors"]
        assert isinstance(cast_authors, set)
        cast_authors.add(str(row["username"]))
        direction = "bullish" if signal > 0.05 else "bearish" if signal < -0.05 else "neutral"
        bucket[direction] = int(bucket[direction]) + 1

    signal_rows: list[dict[str, object]] = []
    for (window, market), bucket in sorted(stats.items()):
        count = int(bucket["count"])
        weight_sum = float(bucket["weight"])
        mean = float(bucket["sum"]) / weight_sum if weight_sum else 0.0
        variance = max(0.0, float(bucket["sq"]) / weight_sum - mean * mean) if weight_sum else 0.0
        effective_n = max(1.0, min(float(count), weight_sum))
        margin = 1.96 * math.sqrt(variance / effective_n)
        authors = bucket["authors"]
        assert isinstance(authors, set)
        diversity = len(authors) / max(1, count)
        confidence = min(1.0, 0.45 * min(1.0, count / 40) + 0.35 * diversity + 0.20 * max(0.0, 1.0 - margin))
        signal_rows.append({
            "window_start": window.isoformat(),
            "market": market,
            "tweet_count": count,
            "unique_authors": len(authors),
            "engagement_total": int(bucket["engagement"]),
            "bullish_count": int(bucket["bullish"]),
            "bearish_count": int(bucket["bearish"]),
            "neutral_count": int(bucket["neutral"]),
            "composite_signal": round(mean, 6),
            "ci95_lower": round(max(-1.0, mean - margin), 6),
            "ci95_upper": round(min(1.0, mean + margin), 6),
            "confidence": round(confidence, 6),
            "manipulation_risk_mean": round(float(bucket["risk"]) / count, 6),
        })

    signals_path = OUTPUT_DIR / "signals_15m.csv"
    with signals_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(signal_rows[0].keys()))
        writer.writeheader()
        writer.writerows(signal_rows)

    weighted = sum(float(r["composite_signal"]) * int(r["tweet_count"]) for r in signal_rows)
    overall = weighted / len(rows)
    label = "bullish" if overall > 0.08 else "bearish" if overall < -0.08 else "neutral"
    summary = {
        "dataset": "synthetic demonstration data",
        "tweet_count": len(rows),
        "window_count": len(signal_rows),
        "period_start": min(str(r["timestamp"]) for r in rows),
        "period_end": max(str(r["timestamp"]) for r in rows),
        "overall_signal": round(overall, 6),
        "overall_label": label,
        "warning": "Synthetic output for reproducibility; not a market conclusion or financial advice.",
    }
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    plot_signal_series(signals_path, OUTPUT_DIR / "signals.png")


if __name__ == "__main__":
    main()
