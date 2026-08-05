from market_intel.collectors.parsing import parse_compact_count


def test_compact_count_parser() -> None:
    assert parse_compact_count("1,234 Likes") == 1234
    assert parse_compact_count("2.5K") == 2500
    assert parse_compact_count("1.2M views") == 1_200_000
    assert parse_compact_count(None) == 0
