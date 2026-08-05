from __future__ import annotations

import logging
import random
import re
import time
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import quote

from selenium import webdriver
from selenium.common.exceptions import (
    JavascriptException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from market_intel.collectors.base import Collector
from market_intel.collectors.parsing import parse_compact_count
from market_intel.config import Settings
from market_intel.models import TweetRecord

logger = logging.getLogger(__name__)

_MENTION_RE = re.compile(r"(?<!\w)@([A-Za-z0-9_]{1,15})")
_HASHTAG_RE = re.compile(r"(?<!\w)#([\w\u0900-\u097F]+)", re.UNICODE)
_ACCESS_WARNING_MARKERS = (
    "rate limit exceeded",
    "verify your identity",
    "unusual activity",
    "automated requests",
    "account is locked",
    "temporarily limited",
)


class SeleniumXCollector(Collector):
    """Collect posts rendered in X's web UI through a visible browser session.

    The adapter deliberately excludes CAPTCHA bypass, stealth drivers, browser
    fingerprint spoofing, account rotation, proxy rotation, and private endpoint
    reverse engineering. It stops and reports a clear error when X displays an
    authentication, verification, or access-limitation screen.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.x_authorized:
            raise PermissionError(
                "Live X collection is disabled. Set X_SCRAPING_AUTHORIZED=true only "
                "after obtaining the required authorization and reviewing X's terms."
            )
        self.settings = settings
        self.driver = self._build_driver()

    def _build_driver(self) -> webdriver.Chrome:
        options = Options()
        if self.settings.x_headless:
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1440,1100")
        options.add_argument("--disable-notifications")
        options.add_argument("--lang=en-IN")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        if self.settings.x_profile_dir:
            options.add_argument(f"--user-data-dir={self.settings.x_profile_dir}")
        if self.settings.x_profile_name:
            options.add_argument(f"--profile-directory={self.settings.x_profile_name}")

        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(self.settings.page_load_timeout_seconds)
        return driver

    def close(self) -> None:
        try:
            self.driver.quit()
        except WebDriverException:
            logger.exception("Failed to close browser cleanly")

    def __enter__(self) -> "SeleniumXCollector":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def collect(
        self,
        *,
        queries: tuple[str, ...],
        cutoff: datetime,
        target: int,
    ) -> Iterable[TweetRecord]:
        seen_ids: set[str] = set()
        yielded = 0

        for query_index, configured_query in enumerate(queries, start=1):
            if yielded >= target:
                break

            query = self._build_query(configured_query, cutoff)
            url = f"https://x.com/search?q={quote(query)}&src=typed_query&f=live"
            logger.info(
                "Opening search query",
                extra={"query": query, "query_index": query_index},
            )
            self._open(url)
            self._assert_accessible()
            self._wait_for_initial_results()

            no_progress_rounds = 0
            previous_seen = len(seen_ids)

            for scroll_index in range(self.settings.max_scrolls_per_query):
                self._assert_accessible()

                for record in self._extract_visible(configured_query):
                    if record.timestamp < cutoff:
                        continue
                    if record.tweet_id in seen_ids:
                        continue

                    seen_ids.add(record.tweet_id)
                    yielded += 1
                    yield record

                    if yielded >= target:
                        return

                if len(seen_ids) == previous_seen:
                    no_progress_rounds += 1
                else:
                    no_progress_rounds = 0
                    previous_seen = len(seen_ids)

                if no_progress_rounds >= self.settings.no_progress_scroll_limit:
                    logger.warning(
                        "Stopping query after repeated no-progress scrolls",
                        extra={
                            "query": query,
                            "count": len(seen_ids),
                            "no_progress_rounds": no_progress_rounds,
                        },
                    )
                    break

                self._scroll_once(scroll_index)

    def _build_query(self, configured_query: str, cutoff: datetime) -> str:
        parts = [configured_query, f"since:{cutoff.date().isoformat()}"]
        if self.settings.x_exclude_retweets:
            parts.append("-filter:retweets")
        return " ".join(parts)

    def _open(self, url: str) -> None:
        for attempt in range(1, 4):
            try:
                self.driver.get(url)
                WebDriverWait(self.driver, 20).until(
                    lambda driver: driver.execute_script(
                        "return document.readyState"
                    )
                    == "complete"
                )
                return
            except (TimeoutException, WebDriverException):
                logger.exception("Page load failed", extra={"attempt": attempt})
                if attempt == 3:
                    raise
                time.sleep(2**attempt)

    def _wait_for_initial_results(self) -> None:
        """Allow X's client-rendered search timeline to become available."""

        try:
            WebDriverWait(self.driver, 20).until(
                lambda driver: bool(
                    driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
                )
                or "no results" in driver.find_element(By.TAG_NAME, "body").text.lower()
            )
        except (TimeoutException, NoSuchElementException):
            logger.warning(
                "Search timeline did not expose an initial tweet within the wait window",
                extra={"url": self.driver.current_url},
            )

    def _assert_accessible(self) -> None:
        current = self.driver.current_url.lower()
        if "/login" in current or "/i/flow/login" in current:
            raise RuntimeError(
                "X requires authentication. Log in manually with the Chrome profile "
                "configured by X_CHROME_PROFILE_DIR, close that Chrome window, and rerun."
            )

        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
        except NoSuchElementException:
            return

        marker = next(
            (candidate for candidate in _ACCESS_WARNING_MARKERS if candidate in body_text),
            None,
        )
        if marker:
            raise RuntimeError(
                f"X displayed an access or verification screen containing: {marker!r}. "
                "The collector stopped without attempting to bypass it."
            )

    def _scroll_once(self, scroll_index: int) -> None:
        try:
            distance = 900 + min(scroll_index, 30) * 25
            self.driver.execute_script("window.scrollBy(0, arguments[0]);", distance)
        except JavascriptException as exc:
            raise RuntimeError("Could not scroll the X timeline") from exc

        delay = random.uniform(
            self.settings.min_scroll_delay_seconds,
            self.settings.max_scroll_delay_seconds,
        )
        time.sleep(delay)

    def _extract_visible(self, query_tag: str) -> list[TweetRecord]:
        records: list[TweetRecord] = []
        articles = self.driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")

        for article in articles:
            try:
                record = self._parse_article(article, query_tag)
                if record:
                    records.append(record)
            except (NoSuchElementException, StaleElementReferenceException, ValueError):
                continue
            except Exception:
                logger.exception("Unexpected tweet parsing error")

        return records

    def _parse_article(self, article, query_tag: str) -> TweetRecord | None:
        time_el = article.find_element(By.CSS_SELECTOR, "time[datetime]")
        raw_timestamp = time_el.get_attribute("datetime")
        if not raw_timestamp:
            return None
        timestamp = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))

        link_el = time_el.find_element(By.XPATH, "./ancestor::a[contains(@href, '/status/')]")
        href = link_el.get_attribute("href") or ""
        status_match = re.search(r"/status/(\d+)", href)
        if not status_match:
            return None
        tweet_id = status_match.group(1)

        username = self._extract_username(article)
        content_nodes = article.find_elements(By.CSS_SELECTOR, "[data-testid='tweetText']")
        content = content_nodes[0].text if content_nodes else ""
        if not content:
            return None

        mentions = sorted({mention.lower() for mention in _MENTION_RE.findall(content)})
        hashtags = sorted({hashtag.lower() for hashtag in _HASHTAG_RE.findall(content)})

        return TweetRecord(
            tweet_id=tweet_id,
            username=username,
            timestamp=timestamp.astimezone(timezone.utc),
            content=content,
            reply_count=self._metric(article, "reply"),
            repost_count=self._metric(article, "retweet"),
            like_count=self._metric(article, "like"),
            bookmark_count=self._metric(article, "bookmark"),
            view_count=self._views(article),
            mentions=mentions,
            hashtags=hashtags,
            url=href,
            query_tag=query_tag,
        )

    @staticmethod
    def _extract_username(article) -> str:
        links = article.find_elements(By.CSS_SELECTOR, "[data-testid='User-Name'] a[href^='/']")
        for link in links:
            href = link.get_attribute("href") or ""
            path = href.rstrip("/").split("/")[-1]
            if path and path not in {"home", "explore", "search"} and not path.startswith("i"):
                return path.lstrip("@").lower()
        return "unknown"

    @staticmethod
    def _metric(article, test_id: str) -> int:
        nodes = article.find_elements(By.CSS_SELECTOR, f"[data-testid='{test_id}']")
        if not nodes:
            return 0
        node = nodes[0]
        return parse_compact_count(node.get_attribute("aria-label") or node.text)

    @staticmethod
    def _views(article) -> int:
        nodes = article.find_elements(By.CSS_SELECTOR, "a[href$='/analytics']")
        if not nodes:
            return 0
        return parse_compact_count(nodes[0].get_attribute("aria-label") or nodes[0].text)