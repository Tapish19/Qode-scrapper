from __future__ import annotations

import hashlib
import logging
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from market_intel.collectors.base import Collector
from market_intel.config import Settings
from market_intel.processing.concurrent import bounded_parallel_map
from market_intel.processing.normalize import clean_record
from market_intel.storage.dedupe import DedupeIndex
from market_intel.storage.parquet_store import ParquetTweetStore

logger = logging.getLogger(__name__)


def _dedupe_path(settings: Settings, output_path: Path) -> Path:
    """Return a stable per-dataset dedupe database path."""

    identity = str(output_path.resolve()).casefold()
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return settings.data_dir / "state" / f"dedupe-{suffix}.sqlite3"


def run_collection(
    collector: Collector,
    settings: Settings,
    *,
    target: int,
    hours: int,
    output_path: Path,
) -> dict[str, int | bool | str]:
    """Collect until the output dataset contains ``target`` unique records.

    Existing Parquet rows are seeded into a per-output SQLite index, so rerunning
    ``--target 2000`` resumes toward a cumulative total of 2,000 rather than trying
    to add another 2,000 on every invocation.
    """

    if target <= 0:
        raise ValueError("target must be greater than zero")
    if hours <= 0:
        raise ValueError("hours must be greater than zero")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    store = ParquetTweetStore(output_path, batch_size=settings.parquet_batch_size)
    dedupe_path = _dedupe_path(settings, output_path)

    accepted = 0
    duplicates = 0

    with DedupeIndex(dedupe_path) as index:
        index.seed_tweet_ids(store.iter_tweet_ids())
        existing_unique = len(set(store.iter_tweet_ids(cutoff=cutoff)))
        remaining = max(target - existing_unique, 0)

        if remaining == 0:
            return {
                "requested_total": target,
                "existing_unique": existing_unique,
                "accepted_this_run": 0,
                "duplicates_this_run": 0,
                "written_this_run": 0,
                "total_unique": existing_unique,
                "remaining": 0,
                "target_met": True,
                "dedupe_index": str(dedupe_path),
            }

        raw_target = max(
            remaining + 500,
            math.ceil(remaining * settings.raw_candidate_multiplier),
        )

        def unique_records():
            nonlocal accepted, duplicates
            raw_records = collector.collect(
                queries=settings.search_queries,
                cutoff=cutoff,
                target=raw_target,
            )
            cleaned_records = bounded_parallel_map(
                clean_record,
                raw_records,
                workers=settings.processing_workers,
                max_pending=settings.max_pending_records,
            )

            for record in cleaned_records:
                if not index.add_if_new(record.fingerprint, record.tweet_id):
                    duplicates += 1
                    continue
                accepted += 1
                yield record
                if accepted >= remaining:
                    return

        written = store.write(unique_records())
        total_unique = existing_unique + accepted

    result: dict[str, int | bool | str] = {
        "requested_total": target,
        "existing_unique": existing_unique,
        "accepted_this_run": accepted,
        "duplicates_this_run": duplicates,
        "written_this_run": written,
        "total_unique": total_unique,
        "remaining": max(target - total_unique, 0),
        "target_met": total_unique >= target,
        "dedupe_index": str(dedupe_path),
    }
    logger.info(
        "Collection complete",
        extra={
            "written_this_run": written,
            "total_unique": total_unique,
            "path": str(output_path),
        },
    )
    return result