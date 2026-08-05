from __future__ import annotations

from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from collections.abc import Callable, Iterable, Iterator
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")


def bounded_parallel_map(
    function: Callable[[T], R],
    items: Iterable[T],
    *,
    workers: int,
    max_pending: int | None = None,
) -> Iterator[R]:
    """Map concurrently while preserving order and bounding queued futures.

    The bounded queue prevents a fast source from materializing an entire stream
    in memory. With one worker, this falls back to a direct generator.
    """
    if workers <= 1:
        for item in items:
            yield function(item)
        return

    pending_limit = max_pending or workers * 4
    if pending_limit < workers:
        pending_limit = workers

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="normalize") as executor:
        pending: deque[Future[R]] = deque()
        for item in items:
            pending.append(executor.submit(function, item))
            if len(pending) >= pending_limit:
                yield pending.popleft().result()
        while pending:
            yield pending.popleft().result()
