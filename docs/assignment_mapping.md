# Assignment Requirement Mapping

| Assignment requirement | Implementation |
|---|---|
| Scrape Indian-market discussions | `market_intel/collectors/x_selenium.py` |
| Hashtags | Configured in `Settings.hashtags` |
| Required fields | `TweetRecord` and `TWEET_SCHEMA` |
| Last 24 hours | UTC cutoff in `run_collection`; exact timestamp filter in collector |
| Minimum target | `--target 2000`; stops at target or source exhaustion |
| No paid/Twitter API | Uses Selenium WebDriver only; no X API dependency |
| Efficient real-time structures | generator pipeline, local set, bounded future queue, window accumulators |
| Rate limiting/anti-bot constraints | conservative pacing, bounded retries, no-progress circuit breaker, no control bypass |
| Time/space optimization | streaming generators, bounded batches, sparse vectors, aggregate-only plotting |
| Error handling/logging | JSON logger, page-load retries, parse isolation, lifecycle cleanup |
| Production documentation | README, technical design, notice, docstrings, type hints |
| Clean and normalize | `processing/normalize.py` |
| Parquet schema | `storage/parquet_store.py`; Zstd, dictionary encoding, date/hour partitions |
| Deduplication | local tweet-ID set + persistent SQLite SHA-256 index |
| Unicode/Indian languages | NFKC normalization preserving Devanagari, mixed text, and emoji |
| Text-to-signal vectors | batched `HashingVectorizer` sparse CSR output |
| Custom feature engineering | finance lexicon, negation, manipulation risk, engagement, reach, recency |
| Low-memory visualization | aggregate scan plus deterministic point sampling |
| Signal aggregation | 15-minute/market weighted composite signal |
| Confidence intervals | weighted variance and 95% normal-approximation interval |
| Concurrent processing | bounded `ThreadPoolExecutor` normalizer |
| 10x scalability | partitioned dataset and documented distributed migration path |
| Sample outputs | `data/sample/tweets_preview.csv` and `data/output/*` |
| Automated tests | unit tests and full Parquet integration test |
| Professional practices | package metadata, CI, Dockerfile, Makefile, environment example, MIT license |
