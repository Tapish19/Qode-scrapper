from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable

from market_intel.models import TweetRecord


class Collector(ABC):
    @abstractmethod
    def collect(
        self,
        *,
        queries: tuple[str, ...],
        cutoff: datetime,
        target: int,
    ) -> Iterable[TweetRecord]:
        """Yield collected records until the target or source exhaustion."""