from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


def plot_signal_series(csv_path: Path, output_path: Path, max_points: int = 600) -> None:
    """Plot aggregated signals, retaining bounded memory via deterministic sampling."""
    series: dict[str, list[tuple[datetime, float, float, float]]] = defaultdict(list)
    with csv_path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            series[row["market"]].append(
                (
                    datetime.fromisoformat(row["window_start"]),
                    float(row["composite_signal"]),
                    float(row["ci95_lower"]),
                    float(row["ci95_upper"]),
                )
            )

    fig, ax = plt.subplots(figsize=(12, 6))
    for market, points in sorted(series.items()):
        stride = max(1, len(points) // max_points)
        sampled = points[::stride]
        x = [p[0] for p in sampled]
        y = [p[1] for p in sampled]
        low = [p[2] for p in sampled]
        high = [p[3] for p in sampled]
        ax.plot(x, y, label=market)
        ax.fill_between(x, low, high, alpha=0.12)

    ax.axhline(0.0, linewidth=1)
    ax.set_title("Indian Market Social Composite Signal (15-minute windows)")
    ax.set_xlabel("UTC time")
    ax.set_ylabel("Signal [-1 bearish, +1 bullish]")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
