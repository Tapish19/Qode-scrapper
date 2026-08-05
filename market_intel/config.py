from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_DEFAULT_SEARCH_QUERIES: tuple[str, ...] = (
    '(#nifty50 OR #nifty OR "Nifty 50")',
    '(#banknifty OR #niftybank OR "Bank Nifty")',
    '(#sensex OR SENSEX)',
    '(#intraday OR "intraday trading") (NIFTY OR BANKNIFTY OR NSE OR BSE)',
    '(#stockmarketindia OR #indianstockmarket OR "Indian stock market")',
    '(NSE OR BSE) (stock OR stocks OR shares OR market)',
    '(NIFTY OR BANKNIFTY) (CE OR PE OR call OR put OR options)',
    '(NIFTY OR SENSEX) (bullish OR bearish OR breakout OR breakdown)',
)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _load_search_queries() -> tuple[str, ...]:
    """Load one query per line from a configurable UTF-8 text file.

    Blank lines and lines beginning with ``# `` (hash followed by a space) are
    treated as comments. Hashtag queries such as ``#nifty50`` remain valid.
    """

    configured_path = Path(os.getenv("X_SEARCH_QUERIES_FILE", "config/search_queries.txt"))
    if not configured_path.exists():
        return _DEFAULT_SEARCH_QUERIES

    queries: list[str] = []
    for raw_line in configured_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("# "):
            continue
        queries.append(line)

    return tuple(dict.fromkeys(queries)) or _DEFAULT_SEARCH_QUERIES


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "data")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())

    x_authorized: bool = field(
        default_factory=lambda: _env_bool("X_SCRAPING_AUTHORIZED", False)
    )
    x_profile_dir: str | None = field(
        default_factory=lambda: os.getenv("X_CHROME_PROFILE_DIR") or None
    )
    x_profile_name: str | None = field(
        default_factory=lambda: os.getenv("X_CHROME_PROFILE_NAME") or None
    )
    x_headless: bool = field(default_factory=lambda: _env_bool("X_HEADLESS", False))
    x_exclude_retweets: bool = field(
        default_factory=lambda: _env_bool("X_EXCLUDE_RETWEETS", True)
    )

    page_load_timeout_seconds: int = field(
        default_factory=lambda: _env_int("PAGE_LOAD_TIMEOUT_SECONDS", 30)
    )
    min_scroll_delay_seconds: float = field(
        default_factory=lambda: _env_float("MIN_SCROLL_DELAY_SECONDS", 1.8)
    )
    max_scroll_delay_seconds: float = field(
        default_factory=lambda: _env_float("MAX_SCROLL_DELAY_SECONDS", 3.0)
    )
    max_scrolls_per_query: int = field(
        default_factory=lambda: _env_int("MAX_SCROLLS_PER_QUERY", 220)
    )
    no_progress_scroll_limit: int = field(
        default_factory=lambda: _env_int("NO_PROGRESS_SCROLL_LIMIT", 12)
    )

    parquet_batch_size: int = field(
        default_factory=lambda: _env_int("PARQUET_BATCH_SIZE", 500)
    )
    processing_workers: int = field(
        default_factory=lambda: _env_int(
            "PROCESSING_WORKERS", min(4, os.cpu_count() or 1)
        )
    )
    max_pending_records: int = field(
        default_factory=lambda: _env_int("MAX_PENDING_RECORDS", 32)
    )
    raw_candidate_multiplier: float = field(
        default_factory=lambda: _env_float("RAW_CANDIDATE_MULTIPLIER", 2.5)
    )

    search_queries: tuple[str, ...] = field(default_factory=_load_search_queries)

    def __post_init__(self) -> None:
        if self.min_scroll_delay_seconds <= 0:
            raise ValueError("MIN_SCROLL_DELAY_SECONDS must be greater than zero")
        if self.max_scroll_delay_seconds < self.min_scroll_delay_seconds:
            raise ValueError(
                "MAX_SCROLL_DELAY_SECONDS must be greater than or equal to "
                "MIN_SCROLL_DELAY_SECONDS"
            )
        if self.max_scrolls_per_query <= 0:
            raise ValueError("MAX_SCROLLS_PER_QUERY must be greater than zero")
        if self.no_progress_scroll_limit <= 0:
            raise ValueError("NO_PROGRESS_SCROLL_LIMIT must be greater than zero")
        if self.raw_candidate_multiplier < 1:
            raise ValueError("RAW_CANDIDATE_MULTIPLIER must be at least 1")
        if not self.search_queries:
            raise ValueError("At least one X search query is required")

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "raw").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "processed").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "output").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "state").mkdir(parents=True, exist_ok=True)