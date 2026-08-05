from __future__ import annotations

import json
from pathlib import Path

import pyarrow.dataset as ds
from scipy import sparse
from sklearn.feature_extraction.text import HashingVectorizer


def export_hashed_vectors(
    dataset_path: Path,
    output_dir: Path,
    *,
    n_features: int = 2**14,
    batch_size: int = 1_000,
) -> dict[str, int]:
    """Vectorize text in bounded batches and store sparse CSR matrices.

    HashingVectorizer has fixed memory usage and does not require a global
    vocabulary fit, making it suitable for a continuous stream.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = ds.dataset(str(dataset_path), format="parquet", partitioning="hive")
    scanner = dataset.scanner(columns=["tweet_id", "normalized_content"], batch_size=batch_size)
    vectorizer = HashingVectorizer(
        n_features=n_features,
        alternate_sign=False,
        norm="l2",
        ngram_range=(1, 2),
        lowercase=False,
    )

    total_rows = 0
    batch_count = 0
    for batch_count, batch in enumerate(scanner.to_batches(), start=1):
        rows = batch.to_pylist()
        texts = [row["normalized_content"] or "" for row in rows]
        ids = [row["tweet_id"] for row in rows]
        matrix = vectorizer.transform(texts).tocsr()
        sparse.save_npz(output_dir / f"vectors-{batch_count:05d}.npz", matrix, compressed=True)
        (output_dir / f"tweet-ids-{batch_count:05d}.json").write_text(
            json.dumps(ids, ensure_ascii=False), encoding="utf-8"
        )
        total_rows += len(rows)

    metadata = {
        "rows": total_rows,
        "batches": batch_count,
        "features": n_features,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata
