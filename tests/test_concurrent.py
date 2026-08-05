from market_intel.processing.concurrent import bounded_parallel_map


def test_bounded_parallel_map_preserves_order() -> None:
    result = list(bounded_parallel_map(lambda x: x * x, range(20), workers=4, max_pending=5))
    assert result == [x * x for x in range(20)]
