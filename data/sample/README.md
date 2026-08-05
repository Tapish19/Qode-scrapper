# Sample Data

`tweets_preview.csv` contains 2,500 **synthetic** posts spanning a fixed 24-hour period. It exists only so reviewers can inspect the schema and multilingual examples without accessing X.

The production generator writes partitioned Parquet to `data/sample/tweets/`:

```bash
python -m market_intel generate-sample --count 2500 --output data/sample/tweets
```

No row in the preview represents a real X user or a real market observation.
