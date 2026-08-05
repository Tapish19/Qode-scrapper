from datetime import datetime, timedelta, timezone

from market_intel.analysis.features import extract_text_features, tweet_signal


def test_bullish_and_bearish_polarity() -> None:
    bullish = extract_text_features("NIFTY breakout buy target strong")
    bearish = extract_text_features("NIFTY breakdown sell weak downside")
    assert bullish.polarity > 0
    assert bearish.polarity < 0


def test_manipulation_language_is_discounted() -> None:
    risky = extract_text_features("SURE SHOT guaranteed double money 100%")
    normal = extract_text_features("bullish breakout above support")
    assert risky.manipulation_risk > normal.manipulation_risk


def test_old_tweet_has_lower_weight() -> None:
    now = datetime.now(timezone.utc)
    _, fresh_weight = tweet_signal(
        polarity=1.0,
        engagement_total=10,
        view_count=100,
        timestamp=now,
        manipulation_risk=0.0,
        now=now,
    )
    _, old_weight = tweet_signal(
        polarity=1.0,
        engagement_total=10,
        view_count=100,
        timestamp=now - timedelta(hours=20),
        manipulation_risk=0.0,
        now=now,
    )
    assert fresh_weight > old_weight
