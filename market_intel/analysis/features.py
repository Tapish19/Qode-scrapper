from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone

BULLISH_TERMS = {
    "buy", "bullish", "breakout", "upside", "rally", "long", "target", "strong",
    "accumulate", "support", " तेजी ", "तेजी", "खरीद", "खरीदो", "ऊपर", "उछाल",
    "bull", "recovery", "outperform", "green",
}
BEARISH_TERMS = {
    "sell", "bearish", "breakdown", "downside", "crash", "short", "weak", "fall",
    " गिरावट ", "गिरावट", "मंदी", "बेचो", "नीचे", "loss", "red", "underperform",
}
RISK_TERMS = {
    "sure shot", "guaranteed", "operator", "pump", "upper circuit", "multibagger",
    "100%", "double money", "jackpot", "inside news", "fixed target",
}
NEGATIONS = {"not", "no", "never", "नहीं", "मत"}
_TOKEN_RE = re.compile(r"[#@]?[\w\u0900-\u097F%]+", re.UNICODE)


@dataclass(slots=True)
class TextFeatures:
    polarity: float
    bullish_hits: int
    bearish_hits: int
    manipulation_risk: float
    uppercase_ratio: float
    exclamation_count: int


def extract_text_features(text: str) -> TextFeatures:
    lowered = f" {text.lower()} "
    tokens = _TOKEN_RE.findall(lowered)

    bullish = sum(1 for term in BULLISH_TERMS if term.strip() in lowered)
    bearish = sum(1 for term in BEARISH_TERMS if term.strip() in lowered)

    for idx, token in enumerate(tokens):
        if token in NEGATIONS and idx + 1 < len(tokens):
            next_token = tokens[idx + 1]
            if next_token in BULLISH_TERMS:
                bullish = max(0, bullish - 1)
                bearish += 1
            elif next_token in BEARISH_TERMS:
                bearish = max(0, bearish - 1)
                bullish += 1

    denominator = bullish + bearish
    polarity = (bullish - bearish) / denominator if denominator else 0.0
    risk_hits = sum(1 for term in RISK_TERMS if term in lowered)
    alpha = [c for c in text if c.isalpha()]
    uppercase_ratio = sum(c.isupper() for c in alpha) / len(alpha) if alpha else 0.0
    manipulation_risk = min(1.0, risk_hits * 0.3 + max(0.0, uppercase_ratio - 0.45))

    return TextFeatures(
        polarity=polarity,
        bullish_hits=bullish,
        bearish_hits=bearish,
        manipulation_risk=manipulation_risk,
        uppercase_ratio=uppercase_ratio,
        exclamation_count=text.count("!"),
    )


def tweet_signal(
    *,
    polarity: float,
    engagement_total: int,
    view_count: int,
    timestamp: datetime,
    manipulation_risk: float,
    now: datetime | None = None,
) -> tuple[float, float]:
    """Return (signal, weight), each bounded for stable aggregation."""
    current = now or datetime.now(timezone.utc)
    age_hours = max(0.0, (current - timestamp).total_seconds() / 3600)
    recency = math.exp(-age_hours / 12.0)
    engagement = math.log1p(max(0, engagement_total))
    reach = math.log1p(max(0, view_count))
    social_weight = min(3.0, 1.0 + 0.22 * engagement + 0.08 * reach)
    quality_discount = 1.0 - 0.65 * manipulation_risk
    weight = max(0.05, recency * social_weight * quality_discount)
    signal = max(-1.0, min(1.0, polarity * quality_discount))
    return signal, weight
