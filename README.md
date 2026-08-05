# Indian Market Intelligence Pipeline

A production-oriented Python system that collects authorized X/Twitter market discussions, normalizes multilingual text, stores deduplicated records as partitioned Parquet, and converts social text into bounded quantitative signals for Indian equity-market research.

> **Compliance note:** X's current Terms of Service prohibit scraping without prior written permission. The Selenium collector is therefore disabled by default and intentionally excludes CAPTCHA bypass, stealth drivers, fingerprint spoofing, private endpoint reverse engineering, proxy rotation, and other control-evasion techniques. Use the live collector only when you have the required authorization. The synthetic-data workflow runs without X access and demonstrates the complete engineering pipeline.

## What this repository demonstrates

- Selenium collection through a normal, visible browser session
- Search coverage for `#nifty50`, `#sensex`, `#intraday`, and `#banknifty`
- Username, UTC timestamp, content, replies, reposts, likes, views, bookmarks, mentions, hashtags, URL, and query source
- Unicode NFKC normalization that preserves Devanagari, mixed Hinglish, and emoji
- Persistent SQLite deduplication plus Parquet analytical storage
- Zstandard-compressed, date/hour-partitioned Parquet datasets
- Fixed-memory HashingVectorizer output in sparse CSR batches
- Finance-aware text polarity, engagement weighting, recency decay, manipulation-risk discounting, and 95% confidence intervals
- Bounded-memory visualization from 15-minute aggregates
- JSON logging, retries, explicit waits, unit tests, integration test, CI, Dockerfile, and typed modular structure

## Repository layout

```text
market_intel/
  collectors/       Selenium collector and collector interface
  processing/       Unicode cleaning, normalization, fingerprinting
  storage/          SQLite dedupe index and partitioned Parquet writer
  analysis/         text features, sparse vectors, signals, charts
  cli.py             command-line entry point
  pipeline.py        collection orchestration
  sample_data.py     clearly synthetic 24-hour demonstration dataset
tests/               unit and integration tests
docs/                architecture and technical decisions
data/sample/         checked-in synthetic CSV preview; generated Parquet goes here
data/output/         checked-in sample signals, summary, and chart
```

## Setup

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
```

Activate it:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

Install:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
```

On Windows, copy `.env.example` manually if `cp` is unavailable.

## Run the complete pipeline without X access

Generate 2,500 clearly synthetic posts distributed over the last 24 hours:

```bash
python -m market_intel generate-sample \
  --count 2500 \
  --output data/sample/tweets
```

Analyze them:

```bash
python -m market_intel analyze --input data/raw/tweets --output data/output_real
```

Generated outputs:

```text
data/output/signals_15m.csv
data/output/summary.json
data/output/signals.png
data/output/vectors/metadata.json
data/output/vectors/vectors-*.npz
data/output/vectors/tweet-ids-*.json
```

## Checked-in sample artifacts

The repository includes a **synthetic** 2,500-row CSV preview and matching analysis outputs so reviewers can inspect results immediately:

```text
data/sample/tweets_preview.csv
data/output/signals_15m.csv
data/output/summary.json
data/output/signals.png
```

The production command writes partitioned Parquet to `data/sample/tweets/`. The CSV preview is not used as a substitute for the production storage path; it is only a portable review artifact.

## Live X Data Collection

The production pipeline collects real public X posts related to Indian equity and derivatives markets using Selenium.

The collector does not use:

- Twitter/X API
- Paid APIs
- Third-party paid scraping services

The search queries are configured in:

```text
config/search_queries.txt
```


1. Create a dedicated Chrome profile and sign in manually.
2. Close Chrome before reusing the same profile from Selenium.
3. Configure `.env`:

```dotenv
X_SCRAPING_AUTHORIZED=true
X_CHROME_PROFILE_DIR=C:/Users/YOUR_NAME/selenium-x-profile-v4
X_CHROME_PROFILE_NAME=Default
X_HEADLESS=false
X_SEARCH_QUERIES_FILE=config/search_queries.txt

```

Run:

```bash
python -m market_intel collect \
  --target 2000 \
  --hours 24 \
  --output data/raw/tweets
```

Then analyze:

```bash
python -m market_intel analyze \
  --input data/raw/tweets \
  --output data/output
```

The collector stops when it reaches the target, exhausts the configured scroll budget, or repeatedly makes no progress. X's DOM and search behavior can change, so selectors are isolated in one adapter for maintainability.

## Signal methodology

Each post receives:

1. **Text polarity:** finance-specific English, Hindi, and common Hinglish terms, with simple negation handling.
2. **Manipulation-risk score:** discounts phrases such as “guaranteed,” “sure shot,” “operator,” and “double money.”
3. **Engagement/reach weight:** logarithmic scaling prevents viral posts from dominating linearly.
4. **Recency weight:** exponential decay with a 12-hour time constant.
5. **Composite signal:** bounded to `[-1, +1]`, where negative is bearish and positive is bullish.

Posts are aggregated by market tag and 15-minute UTC window. The output includes a weighted mean, 95% confidence interval, author diversity, bullish/bearish/neutral counts, engagement, and confidence score.

This is a research signal, not financial advice and not an order-execution strategy.

## Data schema

The Parquet dataset includes:

| Field | Type | Purpose |
|---|---|---|
| `tweet_id` | string | Source identifier |
| `username` | string | Normalized handle |
| `timestamp` | UTC timestamp | Event time |
| `content` | string | Clean display text |
| `normalized_content` | string | Lowercased analysis text |
| `language_hint` | string | Indic/English/mixed heuristic |
| engagement fields | int64 | Replies, reposts, likes, views, bookmarks |
| `mentions` | list[string] | Extracted handles |
| `hashtags` | list[string] | Normalized hashtags |
| `fingerprint` | string | SHA-256 dedupe key |
| `event_date`, `event_hour` | partition fields | Predicate pruning |

## Performance characteristics

- Visible DOM extraction is source-bound; the pipeline processes records incrementally.
- Membership checks are average `O(1)` in the collector's local set.
- Persistent dedupe uses a SQLite primary-key B-tree, approximately `O(log n)` per insert.
- Cleaning is `O(L)` per post, where `L` is text length.
- Parquet writes are bounded by `PARQUET_BATCH_SIZE` rather than total dataset size.
- Sparse hashing uses fixed dimensionality and batch-bounded memory.
- Aggregation retains one accumulator per `(time window, market)` rather than every post.

For 10x scale, partition files can be consumed by DuckDB, Spark, Polars, Ray, or a cloud object store without changing the record schema.

## Tests and quality checks

```bash
pytest
ruff check .
```

The integration test generates a temporary Parquet dataset, analyzes it, and verifies sparse-vector and signal outputs.

## Known limitations

- X's web UI is dynamic and may change without notice.
- Search results are not guaranteed to be a complete census of all matching posts.
- Engagement counts shown in the UI may be rounded.
- Language detection is deliberately lightweight; production language identification can be added behind the feature interface.
- Lexicon-based direction is interpretable but not equivalent to a trained financial sentiment model.
- A target of exactly 2,000 posts cannot be guaranteed if the authorized source exposes fewer matching results in the requested time window.

See [`docs/technical_design.md`](docs/technical_design.md) for the architecture, trade-offs, scaling plan, and failure handling.
