from market_intel.config import Settings


def test_search_queries_load_from_file(tmp_path, monkeypatch) -> None:
    query_file = tmp_path / "queries.txt"
    query_file.write_text(
        '# comment\n\n#nifty50\n("Bank Nifty" OR #banknifty)\n#nifty50\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("X_SEARCH_QUERIES_FILE", str(query_file))

    settings = Settings()

    assert settings.search_queries == (
        "#nifty50",
        '("Bank Nifty" OR #banknifty)',
    )


def test_invalid_scroll_range_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("MIN_SCROLL_DELAY_SECONDS", "3")
    monkeypatch.setenv("MAX_SCROLL_DELAY_SECONDS", "2")

    try:
        Settings()
    except ValueError as exc:
        assert "MAX_SCROLL_DELAY_SECONDS" in str(exc)
    else:
        raise AssertionError("Expected invalid scroll settings to raise ValueError")