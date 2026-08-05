.PHONY: install test lint sample analyze clean

install:
	python -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .

sample:
	python -m market_intel generate-sample --count 2500 --output data/sample/tweets

analyze:
	python -m market_intel analyze --input data/sample/tweets --output data/output

clean:
	rm -rf data/sample/tweets data/output/* .pytest_cache .ruff_cache
