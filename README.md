# Indian Market Intelligence Pipeline

A production-oriented Python system that collects public Indian stock-market discussions from X using Selenium, normalizes multilingual text, stores deduplicated records in partitioned Parquet format, and converts social-media text into bounded quantitative market signals.

The project is designed around the assignment requirement of collecting at least 2,000 unique posts from the most recent rolling 24-hour window without using the Twitter/X API or any paid API.

> **Compliance note:** The live collector is disabled by default. Enable and use it only when you have the required authorization. The implementation intentionally excludes CAPTCHA bypassing, stealth drivers, fingerprint spoofing, account rotation, proxy rotation, private-endpoint reverse engineering, and other control-evasion techniques.

## What This Repository Demonstrates

- Selenium collection through a normal, visible Chrome browser
- Persistent manually authenticated Chrome sessions
- Configurable Indian-market search queries
- Collection of posts about:
  - NIFTY 50
  - Bank Nifty
  - Sensex
  - NSE and BSE equities
  - Intraday trading
  - Options and derivatives
  - Major Indian listed companies
  - Hindi and Hinglish market discussions
- Extraction of:
  - Username
  - UTC timestamp
  - Post content
  - Replies
  - Reposts
  - Likes
  - Views
  - Bookmarks
  - Mentions
  - Hashtags
  - Original post URL
  - Search-query provenance
- Unicode NFKC normalization
- Devanagari, Hinglish, emoji, and special-character preservation
- Persistent SQLite-backed deduplication
- Zstandard-compressed, date/hour-partitioned Parquet storage
- Sparse numerical text vectors
- Finance-specific feature engineering
- Engagement and recency weighting
- Manipulation-risk discounting
- Composite market signals bounded between `-1` and `+1`
- Fifteen-minute signal aggregation
- 95% confidence intervals
- Memory-efficient visualization
- Structured JSON logging
- Retry handling and explicit Selenium waits
- Unit tests, integration tests, CI configuration, and typed modular code

## Repository Layout

```text
indian-market-intelligence/
├── market_intel/
│   ├── collectors/
│   │   ├── base.py
│   │   └── x_selenium.py
│   ├── processing/
│   │   └── text cleaning, normalization, and fingerprinting
│   ├── storage/
│   │   ├── dedupe.py
│   │   └── parquet_store.py
│   ├── analysis/
│   │   └── vectors, features, signals, aggregation, and charts
│   ├── config.py
│   ├── pipeline.py
│   ├── cli.py
│   ├── sample_data.py
│   └── __main__.py
├── config/
│   └── search_queries.txt
├── tests/
├── docs/
│   ├── technical_design.md
│   └── assignment_mapping.md
├── data/
│   ├── raw/
│   │   └── tweets/
│   ├── output_real/
│   └── state/
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.11 or newer
- Google Chrome
- Windows, Linux, or macOS
- An authenticated X account for authorized live collection
- Internet access during Selenium collection

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/USERNAME/Qode-scrapper.git
cd Qode-scrapper
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the environment

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux or macOS:

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Alternatively:

```bash
python -m pip install -r requirements.txt
```

On Windows, ensure that `tzdata` is installed so PyArrow can read timezone-aware timestamps:

```powershell
python -m pip install tzdata
```

### 5. Create the environment file

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux or macOS:

```bash
cp .env.example .env
```

## Environment Configuration

Example `.env`:

```dotenv
DATA_DIR=data
LOG_LEVEL=INFO

X_SCRAPING_AUTHORIZED=true
X_CHROME_PROFILE_DIR=C:/Users/YOUR_NAME/selenium-x-profile-v4
X_CHROME_PROFILE_NAME=Default
X_HEADLESS=false

X_SEARCH_QUERIES_FILE=config/search_queries.txt
X_EXCLUDE_RETWEETS=true

PAGE_LOAD_TIMEOUT_SECONDS=60
MIN_SCROLL_DELAY_SECONDS=1.8
MAX_SCROLL_DELAY_SECONDS=3.0
MAX_SCROLLS_PER_QUERY=220
NO_PROGRESS_SCROLL_LIMIT=12

PARQUET_BATCH_SIZE=500
PROCESSING_WORKERS=4
MAX_PENDING_RECORDS=32
RAW_CANDIDATE_MULTIPLIER=2.5
```

`X_SCRAPING_AUTHORIZED=true` only enables the collector inside the application. It does not itself grant authorization from X.

Never commit the real `.env` file.

## Search Query Configuration

The live collector reads one X search query per line from:

```text
config/search_queries.txt
```

The application automatically appends the date filter and optionally excludes reposts.

Example query:

```text
(#nifty50 OR #nifty OR "Nifty 50")
```

At runtime, it becomes similar to:

```text
(#nifty50 OR #nifty OR "Nifty 50") since:2026-08-03 -filter:retweets
```

The exact rolling 24-hour cutoff is enforced again in Python after extraction.

Verify that the query file is available:

```powershell
Test-Path .\config\search_queries.txt
```

Expected output:

```text
True
```

Verify how many queries are loaded:

```powershell
python -c "from market_intel.config import Settings; s=Settings(); print('Loaded queries:', len(s.search_queries)); print(*s.search_queries, sep='\n')"
```

## Dedicated Chrome Profile Setup

Do not point Selenium to the normal Chrome data directory under:

```text
C:/Users/YOUR_NAME/AppData/Local/Google/Chrome/User Data
```

Modern Chrome versions may block automation against the default profile, and using the same profile from multiple Chrome processes can cause profile-lock errors.

Create a separate persistent Chrome profile.

Windows PowerShell:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --user-data-dir="C:\Users\YOUR_NAME\selenium-x-profile-v4" `
  --profile-directory="Default" `
  "https://x.com/home"
```

When Chrome opens:

1. Sign in to X manually.
2. Confirm that the X home page loads.
3. Completely close that dedicated Chrome window.
4. Configure the same profile path in `.env`.

Example:

```dotenv
X_CHROME_PROFILE_DIR=C:/Users/YOUR_NAME/selenium-x-profile-v4
X_CHROME_PROFILE_NAME=Default
```

Do not keep this dedicated Chrome profile open before starting the collector. Once the collector opens Chrome, do not manually close or control the Selenium browser while collection is running.

## Live X Data Collection

Run the collector against real public X posts.

### Windows PowerShell

```powershell
python -m market_intel collect --target 2000 --hours 24 --output data/raw/tweets
```

### Linux or macOS

```bash
python -m market_intel collect \
  --target 2000 \
  --hours 24 \
  --output data/raw/tweets
```

The collector:

1. Opens Chrome using the configured persistent profile.
2. Loads each query from `config/search_queries.txt`.
3. Opens the X Latest search timeline.
4. Extracts visible posts incrementally.
5. Rejects posts outside the exact rolling 24-hour window.
6. Normalizes text and engagement values.
7. Deduplicates using tweet IDs and fingerprints.
8. Writes accepted records to partitioned Parquet files.
9. Continues until the cumulative target is reached or available results are exhausted.

The target is cumulative for the active rolling 24-hour window. Existing valid records under `data/raw/tweets` are counted before new collection begins.

Example progress result:

```json
{
  "requested_total": 2000,
  "existing_unique": 1329,
  "accepted_this_run": 300,
  "duplicates_this_run": 120,
  "written_this_run": 300,
  "total_unique": 1629,
  "remaining": 371,
  "target_met": false
}
```

The assignment target is complete when the result reports:

```json
{
  "total_unique": 2000,
  "remaining": 0,
  "target_met": true
}
```

The collector may stop before reaching 2,000 when:

- The configured queries are exhausted
- X stops exposing additional search results
- Repeated scrolling produces no new posts
- The scroll budget is exhausted
- A login or verification page appears
- A rate-limit or account-restriction page appears
- The browser session becomes unavailable

## Real Dataset Storage

Real collected posts are stored under:

```text
data/raw/tweets/
```

The files are partitioned by post date and hour:

```text
data/raw/tweets/
└── event_date=YYYY-MM-DD/
    └── event_hour=HH/
        └── part-*.parquet
```

The persistent deduplication index is stored separately under:

```text
data/state/
```

Do not delete the deduplication database while keeping the existing Parquet dataset. Doing so may allow duplicate records to be written during later runs.

## Verify the Collected Dataset

Count all stored Parquet rows:

```powershell
python -c "import pyarrow.dataset as ds; d=ds.dataset(r'data/raw/tweets', format='parquet', partitioning='hive'); print('Stored rows:', d.count_rows())"
```

Inspect the schema:

```powershell
python -c "import pyarrow.dataset as ds; d=ds.dataset(r'data/raw/tweets', format='parquet', partitioning='hive'); print(d.schema)"
```

Inspect five records:

```powershell
python -c "import pyarrow.dataset as ds; d=ds.dataset(r'data/raw/tweets', format='parquet', partitioning='hive'); print(d.head(5).to_pandas()[['tweet_id','username','timestamp','content','url']].to_string(index=False))"
```

## Analyze the Real Dataset

After collecting real posts, run the analysis pipeline.

### Windows PowerShell

```powershell
python -m market_intel analyze --input data/raw/tweets --output data/output_real
```

### Linux or macOS

```bash
python -m market_intel analyze \
  --input data/raw/tweets \
  --output data/output_real
```

Generated artifacts:

```text
data/output_real/signals_15m.csv
data/output_real/summary.json
data/output_real/signals.png
data/output_real/vectors/metadata.json
data/output_real/vectors/vectors-*.npz
data/output_real/vectors/tweet-ids-*.json
```

## Analysis Outputs

### `signals_15m.csv`

Contains time-window market-signal aggregates such as:

```text
window_start
market_tag
tweet_count
unique_authors
bullish_count
bearish_count
neutral_count
composite_signal
confidence_lower
confidence_upper
confidence_score
engagement_total
```

### `summary.json`

Contains overall dataset and signal information such as:

- Number of posts analyzed
- Analysis time window
- Overall composite signal
- Bullish, bearish, or neutral label
- Signal confidence
- Bullish, bearish, and neutral distribution
- Most active market tags
- Aggregate engagement

### `signals.png`

A memory-efficient chart generated from aggregated time windows instead of plotting every post individually.

### Sparse Vector Files

```text
data/output_real/vectors/vectors-*.npz
```

These contain sparse numerical text vectors generated in bounded batches.

Associated tweet IDs are stored in:

```text
data/output_real/vectors/tweet-ids-*.json
```

Vectorization metadata is stored in:

```text
data/output_real/vectors/metadata.json
```

## Signal Methodology

Each post is converted into a numerical market signal using multiple features.

### 1. Text Vectorization

The project uses a fixed-dimensional sparse hashing vectorizer with unigram and bigram features.

This approach provides:

- Bounded memory usage
- No requirement to keep a vocabulary dictionary in memory
- Efficient batch processing
- Compatibility with large and streaming datasets

### 2. Finance-Specific Text Features

The feature pipeline detects market terminology such as:

```text
bullish
bearish
breakout
breakdown
support
resistance
buy
sell
long
short
call
put
CE
PE
gap up
gap down
teji
mandi
upar
weak
crash
```

Simple negation handling is applied so phrases such as:

```text
not bullish
no breakout
not a buy
```

are not treated as ordinary positive signals.

### 3. Manipulation-Risk Discounting

Promotional or potentially manipulative phrases reduce signal confidence.

Examples include:

```text
guaranteed
sure shot
double money
operator game
100% confirmed
risk free
```

### 4. Engagement Weight

Replies, reposts, likes, views, and bookmarks contribute to the post weight.

Logarithmic scaling is used so highly viral posts do not dominate the complete signal linearly.

### 5. Recency Weight

Recent posts receive more weight than older posts.

The implementation uses exponential decay with a configurable time horizon.

### 6. Composite Signal

The final post-level signal is bounded between:

```text
-1.0 = strongly bearish
 0.0 = neutral or uncertain
+1.0 = strongly bullish
```

The signal is intended for market-research analysis. It is not financial advice and is not an automated order-execution strategy.

## Signal Aggregation and Confidence Intervals

Posts are grouped by:

```text
market/index tag + 15-minute UTC window
```

For each group, the analysis calculates:

- Weighted composite signal
- Weighted variance
- 95% confidence interval
- Bullish post count
- Bearish post count
- Neutral post count
- Unique-author count
- Total engagement
- Confidence score

Confidence considers factors such as:

- Number of posts
- Author diversity
- Signal agreement
- Confidence-interval width

## Memory-Efficient Visualization

The visualization layer does not plot every post directly.

Instead, it:

1. Processes records in bounded batches.
2. Aggregates signals into fifteen-minute windows.
3. Keeps one accumulator per market/time window.
4. Samples aggregate points only when the chart exceeds the configured limit.
5. Writes the final visualization without keeping the full raw dataset in plotting memory.

This makes visualization memory usage dependent on the number of aggregate windows rather than the total number of posts.

## Data Schema

The Parquet dataset includes fields such as:

| Field | Type | Purpose |
|---|---|---|
| `tweet_id` | string | Original source identifier |
| `username` | string | Normalized X handle |
| `timestamp` | UTC timestamp | Original post time |
| `content` | string | Clean display text |
| `normalized_content` | string | Analysis-ready normalized text |
| `language_hint` | string | Indic, English, mixed, or unknown heuristic |
| `reply_count` | int64 | Reply engagement |
| `repost_count` | int64 | Repost engagement |
| `like_count` | int64 | Like engagement |
| `view_count` | int64 | View engagement |
| `bookmark_count` | int64 | Bookmark engagement |
| `engagement_total` | int64 | Combined engagement |
| `mentions` | list[string] | Extracted account mentions |
| `hashtags` | list[string] | Extracted normalized hashtags |
| `url` | string | Canonical source URL |
| `query_tag` | string | Search query that found the post |
| `collected_at` | UTC timestamp | Collection time |
| `fingerprint` | string | SHA-256 deduplication key |
| `event_date` | string | Parquet date partition |
| `event_hour` | string | Parquet hour partition |

## Deduplication

The collector uses multiple deduplication layers.

### In-Memory Deduplication

A Python set tracks tweet IDs seen during the active collection run.

Average membership complexity:

```text
O(1)
```

### Persistent Deduplication

SQLite stores accepted tweet IDs and fingerprints across runs.

Approximate index lookup complexity:

```text
O(log n)
```

### Dataset-Aware Deduplication

Existing Parquet tweet IDs are read when continuing a collection so the persistent index can be synchronized with previously stored records.

## Checked-In Analysis Artifacts

The repository includes the analysis results generated from the real collected X dataset:

```text
data/output_real/signals_15m.csv
data/output_real/summary.json
data/output_real/signals.png
data/output_real/vectors/metadata.json
data/output_real/vectors/vectors-*.npz
data/output_real/vectors/tweet-ids-*.json
```

The complete collected dataset remains stored locally as partitioned Parquet under:

```text
data/raw/tweets/
```

The raw dataset may be excluded from a public repository because it can be large and may contain third-party public content. Reviewers can inspect the generated signal outputs, vector metadata, tests, collection logic, and documentation directly from the repository.

Never include:

```text
.env
Chrome profile folders
cookies
login databases
session tokens
OTPs
account passwords
data/state/*.sqlite3
```

## Performance Characteristics

- Visible DOM extraction is limited primarily by the source website.
- Collection records are processed incrementally.
- In-memory duplicate checks are average `O(1)`.
- SQLite-backed persistent duplicate checks are approximately `O(log n)`.
- Text cleaning is `O(L)` per post, where `L` is the text length.
- Parquet writes are bounded by `PARQUET_BATCH_SIZE`.
- Sparse vectorization uses fixed dimensionality.
- Aggregation retains one accumulator per market and time window.
- Visualization uses aggregate points instead of all raw posts.

## Scalability to 10x Data

For approximately 20,000 or more records:

- Increase Parquet partition size carefully.
- Continue using batch-based processing.
- Read only required columns.
- Use predicate pushdown on date and hour partitions.
- Process sparse vector batches independently.
- Use DuckDB or Polars for local analytical queries.
- Use Spark, Ray, or cloud object storage for larger distributed workloads.
- Keep collection, processing, storage, and analysis components independently replaceable.

The Parquet schema does not need to change when moving to these larger processing engines.

## Logging and Error Handling

The project uses structured JSON logs.

Logged events include:

- Search query opened
- Browser timeout
- Retry attempt
- No-progress stopping condition
- Login requirement
- Verification or access restriction
- Number of accepted posts
- Number of duplicates
- Number of records written
- Remaining target count
- Final dataset path

A single page timeout does not necessarily stop the complete collector. Recoverable failures are logged, and the collector may continue to the next query.

## Tests and Quality Checks

Run the complete test suite:

```bash
pytest
```

Run linting:

```bash
ruff check .
```

The tests cover:

- Configuration loading
- Search-query loading
- Unicode normalization
- Deduplication
- Signal feature generation
- Parquet storage
- Analysis outputs
- Sparse-vector artifacts

## Troubleshooting

### `DevToolsActivePort file doesn't exist`

Use a dedicated Chrome profile outside Chrome's default user-data directory.

Do not use:

```text
C:/Users/YOUR_NAME/AppData/Local/Google/Chrome/User Data
```

Use:

```text
C:/Users/YOUR_NAME/selenium-x-profile-v4
```

Close all Chrome windows using the dedicated profile before starting Selenium.

### `The zoneinfo module or pytz package must be installed`

Install timezone data:

```powershell
python -m pip install tzdata
```

If required:

```powershell
python -m pip install pytz
```

### Query file not found

Verify:

```powershell
Test-Path .\config\search_queries.txt
```

Set the path in `.env`:

```dotenv
X_SEARCH_QUERIES_FILE=config/search_queries.txt
```

### Collector finds mostly duplicates

The query may overlap heavily with previous searches. Add relevant market-specific queries to:

```text
config/search_queries.txt
```

Do not delete the deduplication database while retaining the existing Parquet files.

### Collector stops below 2,000

Possible causes include:

- Source exhaustion
- Search-result overlap
- X exposing only part of the timeline
- Posts aging outside the rolling 24-hour window
- Retweets being excluded
- Login or access restrictions
- Dynamic changes in the X web interface

Document the actual result honestly rather than fabricating missing records.

## Known Limitations

- X's web interface can change without notice.
- Search results are not guaranteed to represent every matching post.
- Engagement values displayed by X may be abbreviated or rounded.
- Language detection is intentionally lightweight.
- Lexicon-based market direction is interpretable but not equivalent to a trained financial-language model.
- A target of exactly 2,000 posts cannot be guaranteed when the source exposes fewer matching results.
- Social-media market signals can contain spam, coordinated promotion, sarcasm, and misinformation.
- Generated signals should not be interpreted as guaranteed trading recommendations.

## Assignment Requirement Mapping

| Assignment requirement | Implementation |
|---|---|
| Collect Indian market discussions | Selenium X collector |
| Minimum 2,000 posts | Cumulative rolling-window target |
| Previous 24 hours | X date query plus exact Python cutoff |
| No paid API | Browser-based collection |
| Username and timestamp | Stored in Parquet |
| Content and engagement | Stored as typed fields |
| Mentions and hashtags | Extracted into list columns |
| Efficient processing | Incremental and batch-based pipeline |
| Rate-limit/error handling | Delays, retries, stopping conditions, logging |
| Parquet preferred | Partitioned compressed Parquet |
| Deduplication | In-memory, SQLite, and dataset-aware checks |
| Unicode handling | NFKC normalization with Indic preservation |
| Text-to-signal conversion | Sparse vectors plus custom finance features |
| Memory-efficient plotting | Fifteen-minute aggregation and bounded sampling |
| Composite signals | Weighted bounded signal |
| Confidence intervals | Weighted 95% confidence intervals |
| Concurrent processing | Bounded worker pool |
| 10x scalability | Partitioned storage and replaceable analytics |
| Documentation | README and technical design |
| Tests | Unit and integration tests |

## Disclaimer

This repository is intended for technical evaluation and market-intelligence research.

It is not financial advice, an investment recommendation, or an automated trading system.

Use the live X collector only when you have the required authorization and follow all applicable platform terms, privacy requirements, and local laws.

See [`docs/technical_design.md`](docs/technical_design.md) for architecture details, trade-offs, failure handling, and the scalability plan.
