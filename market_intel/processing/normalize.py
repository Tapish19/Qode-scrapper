from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import timezone

from market_intel.models import TweetRecord

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")
_ZERO_WIDTH_RE = re.compile("[\u200B-\u200D\uFEFF]")
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


def normalize_text(text: str) -> str:
    """Normalize Unicode while preserving Indian-language letters and emoji."""
    value = unicodedata.normalize("NFKC", text)
    value = _ZERO_WIDTH_RE.sub("", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Cc" or ch in "\n\t")
    value = _WHITESPACE_RE.sub(" ", value).strip()
    return value


def text_for_analysis(text: str) -> str:
    value = normalize_text(text).lower()
    value = _URL_RE.sub(" <url> ", value)
    return _WHITESPACE_RE.sub(" ", value).strip()


def detect_language_hint(text: str) -> str:
    has_devanagari = bool(_DEVANAGARI_RE.search(text))
    has_ascii_letters = any("a" <= ch.lower() <= "z" for ch in text)
    if has_devanagari and has_ascii_letters:
        return "hinglish_or_mixed"
    if has_devanagari:
        return "hi_or_indic"
    if has_ascii_letters:
        return "en_or_romanized"
    return "unknown"


def fingerprint_record(record: TweetRecord) -> str:
    if record.tweet_id:
        source = f"id:{record.tweet_id}"
    else:
        minute = record.timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        source = f"fallback:{record.username.lower()}|{minute}|{text_for_analysis(record.content)}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def clean_record(record: TweetRecord) -> TweetRecord:
    record.username = normalize_text(record.username).lstrip("@").lower()
    record.content = normalize_text(record.content)
    record.normalized_content = text_for_analysis(record.content)
    record.mentions = sorted({normalize_text(x).lstrip("@").lower() for x in record.mentions})
    record.hashtags = sorted({normalize_text(x).lstrip("#").lower() for x in record.hashtags})
    record.language_hint = detect_language_hint(record.content)
    record.fingerprint = fingerprint_record(record)
    return record
