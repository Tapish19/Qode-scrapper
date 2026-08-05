from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from market_intel.models import TweetRecord
from market_intel.processing.normalize import clean_record
from market_intel.storage.parquet_store import ParquetTweetStore

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


def generate_sample_dataset(path: Path, count: int = 2_500, seed: int = 42) -> int:
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    tags = ["nifty50", "sensex", "intraday", "banknifty"]
    templates = BULLISH * 4 + BEARISH * 3 + NEUTRAL * 3 + RISKY

    def records():
        for index in range(count):
            content = rng.choice(templates)
            tag = next((tag for tag in tags if f"#{tag}" in content.lower()), rng.choice(tags))
            timestamp = now - timedelta(seconds=rng.randint(0, 24 * 3600 - 1))
            record = TweetRecord(
                tweet_id=f"sample-{index:07d}",
                username=f"sample_trader_{rng.randint(1, 420)}",
                timestamp=timestamp,
                content=content,
                reply_count=rng.randint(0, 30),
                repost_count=rng.randint(0, 80),
                like_count=rng.randint(0, 500),
                view_count=rng.randint(50, 80_000),
                bookmark_count=rng.randint(0, 20),
                mentions=["nseindia"] if rng.random() < 0.08 else [],
                hashtags=[tag],
                url=f"https://x.com/sample/status/sample-{index:07d}",
                query_tag=tag,
            )
            yield clean_record(record)

    return ParquetTweetStore(path, batch_size=500).write(records())
