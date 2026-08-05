from market_intel.storage.dedupe import DedupeIndex


def test_dedupe_index(tmp_path) -> None:
    with DedupeIndex(tmp_path / "dedupe.sqlite3") as index:
        assert index.add_if_new("abc", "1") is True
        assert index.add_if_new("abc", "1") is False
        assert index.add_if_new("different-fingerprint", "1") is False
        assert index.add_if_new("def", "2") is True
        assert index.count() == 2


def test_seed_existing_tweet_ids(tmp_path) -> None:
    with DedupeIndex(tmp_path / "dedupe.sqlite3") as index:
        assert index.seed_tweet_ids(["1", "2", "2", ""]) == 2
        assert index.count() == 2
        assert index.add_if_new("another", "2") is False
