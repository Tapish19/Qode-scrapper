from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class TweetRecord:
    tweet_id: str
    username: str
    timestamp: datetime
    content: str
    reply_count: int = 0
    repost_count: int = 0
    like_count: int = 0
    view_count: int = 0
    bookmark_count: int = 0
    mentions: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    url: str = ""
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    query_tag: str = ""
    normalized_content: str = ""
    language_hint: str = "unknown"
    fingerprint: str = ""

    @property
    def engagement_total(self) -> int:
        return (
            self.reply_count
            + self.repost_count
            + self.like_count
            + self.bookmark_count
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.astimezone(timezone.utc)
        data["collected_at"] = self.collected_at.astimezone(timezone.utc)
        data["engagement_total"] = self.engagement_total
        data["event_date"] = data["timestamp"].strftime("%Y-%m-%d")
        data["event_hour"] = data["timestamp"].strftime("%H")
        return data
