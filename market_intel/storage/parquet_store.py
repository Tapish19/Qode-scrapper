from __future__ import annotations

import uuid
from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.dataset as ds

from market_intel.models import TweetRecord

TWEET_SCHEMA = pa.schema(
    [
        ("tweet_id", pa.string()),
        ("username", pa.string()),
        ("timestamp", pa.timestamp("us", tz="UTC")),
        ("content", pa.string()),
        ("normalized_content", pa.string()),
        ("language_hint", pa.string()),
        ("reply_count", pa.int64()),
        ("repost_count", pa.int64()),
        ("like_count", pa.int64()),
        ("view_count", pa.int64()),
        ("bookmark_count", pa.int64()),
        ("engagement_total", pa.int64()),
        ("mentions", pa.list_(pa.string())),
        ("hashtags", pa.list_(pa.string())),
        ("url", pa.string()),
        ("query_tag", pa.string()),
        ("collected_at", pa.timestamp("us", tz="UTC")),
        ("fingerprint", pa.string()),
        ("event_date", pa.string()),
        ("event_hour", pa.string()),
    ]
)


class ParquetTweetStore:
    """Partitioned Parquet dataset optimized for analytical scans."""

    def __init__(self, root: Path, batch_size: int = 500) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.batch_size = batch_size

    def write(self, records: Iterable[TweetRecord]) -> int:
        buffer: list[dict] = []
        total = 0
        for record in records:
            buffer.append(record.to_dict())
            if len(buffer) >= self.batch_size:
                total += self._flush(buffer)
                buffer.clear()
        if buffer:
            total += self._flush(buffer)
        return total

    def count_rows(self) -> int:
        if not self._has_parquet_files():
            return 0
        return int(self._dataset().count_rows())

    def iter_tweet_ids(
        self,
        *,
        cutoff: datetime | None = None,
        batch_size: int = 4_096,
    ) -> Iterator[str]:
        if not self._has_parquet_files():
            return

        columns = ["tweet_id"] if cutoff is None else ["tweet_id", "timestamp"]
        scanner = self._dataset().scanner(columns=columns, batch_size=batch_size)

        for record_batch in scanner.to_batches():
            id_index = record_batch.schema.get_field_index("tweet_id")
            tweet_ids = record_batch.column(id_index).to_pylist()

            if cutoff is None:
                for value in tweet_ids:
                    if value:
                        yield str(value)
                continue

            timestamp_index = record_batch.schema.get_field_index("timestamp")
            timestamps = record_batch.column(timestamp_index).to_pylist()
            for tweet_id, timestamp in zip(tweet_ids, timestamps, strict=True):
                if tweet_id and timestamp is not None and timestamp >= cutoff:
                    yield str(tweet_id)

    def _dataset(self) -> ds.Dataset:
        return ds.dataset(
            str(self.root),
            format="parquet",
            partitioning="hive",
        )

    def _has_parquet_files(self) -> bool:
        return any(self.root.rglob("*.parquet"))

    def _flush(self, rows: list[dict]) -> int:
        table = pa.Table.from_pylist(rows, schema=TWEET_SCHEMA)
        ds.write_dataset(
            table,
            base_dir=str(self.root),
            format="parquet",
            partitioning=["event_date", "event_hour"],
            partitioning_flavor="hive",
            basename_template=f"part-{uuid.uuid4().hex}-{{i}}.parquet",
            existing_data_behavior="overwrite_or_ignore",
            file_options=ds.ParquetFileFormat().make_write_options(
                compression="zstd",
                use_dictionary=True,
                write_statistics=True,
            ),
            max_rows_per_file=max(self.batch_size * 4, 1_000),
            max_rows_per_group=self.batch_size,
        )
        return len(rows)