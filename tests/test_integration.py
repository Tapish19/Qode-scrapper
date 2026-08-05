import pytest

pytest.importorskip("pyarrow")

from market_intel.analysis.signals import analyze_dataset
from market_intel.analysis.vectorize import export_hashed_vectors
from market_intel.sample_data import generate_sample_dataset


def test_sample_pipeline(tmp_path) -> None:
    dataset = tmp_path / "tweets"
    output = tmp_path / "output"
    assert generate_sample_dataset(dataset, count=120) == 120
    summary = analyze_dataset(dataset, output)
    vectors = export_hashed_vectors(dataset, output / "vectors", n_features=256, batch_size=50)
    assert summary["tweet_count"] == 120
    assert vectors["rows"] == 120
    assert (output / "signals_15m.csv").exists()
