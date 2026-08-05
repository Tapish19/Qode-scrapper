from datetime import datetime, timezone

from market_intel.models import TweetRecord
from market_intel.processing.normalize import clean_record, normalize_text


def test_unicode_normalization_preserves_devanagari_and_emoji() -> None:
    value = normalize_text("  बाजार\u200b  में तेजी 🚀  ")
    assert value == "बाजार में तेजी 🚀"


def test_clean_record_generates_stable_fingerprint() -> None:
    record = TweetRecord(
        tweet_id="123",
        username="@Trader",
        timestamp=datetime.now(timezone.utc),
        content="  #NIFTY50   bullish  ",
        hashtags=["#NIFTY50"],
    )
    cleaned = clean_record(record)
    assert cleaned.username == "trader"
    assert cleaned.normalized_content == "#nifty50 bullish"
    assert cleaned.hashtags == ["nifty50"]
    assert len(cleaned.fingerprint) == 64
