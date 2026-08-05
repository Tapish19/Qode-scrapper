FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY market_intel ./market_intel
RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "-m", "market_intel"]
