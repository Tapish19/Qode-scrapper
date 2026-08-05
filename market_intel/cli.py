from __future__ import annotations

import argparse
import json
from pathlib import Path

from market_intel.analysis.signals import analyze_dataset
from market_intel.analysis.vectorize import export_hashed_vectors
from market_intel.analysis.visualize import plot_signal_series
from market_intel.collectors.x_selenium import SeleniumXCollector
from market_intel.config import Settings
from market_intel.logging_config import configure_logging
from market_intel.pipeline import run_collection
from market_intel.sample_data import generate_sample_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Indian market social intelligence pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    collect = sub.add_parser("collect", help="Collect authorized X data using Selenium")
    collect.add_argument("--target", type=int, default=2_000)
    collect.add_argument("--hours", type=int, default=24)
    collect.add_argument("--output", type=Path, default=Path("data/raw/tweets"))

    sample = sub.add_parser("generate-sample", help="Generate clearly synthetic sample data")
    sample.add_argument("--count", type=int, default=2_500)
    sample.add_argument("--output", type=Path, default=Path("data/sample/tweets"))

    analyze = sub.add_parser("analyze", help="Create vectors, signals and visualization")
    analyze.add_argument("--input", type=Path, required=True)
    analyze.add_argument("--output", type=Path, default=Path("data/output"))
    analyze.add_argument("--window-minutes", type=int, default=15)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings()
    settings.ensure_directories()
    configure_logging(settings.log_level)

    if args.command == "collect":
        with SeleniumXCollector(settings) as collector:
            result = run_collection(
                collector,
                settings,
                target=args.target,
                hours=args.hours,
                output_path=args.output,
            )
        print(json.dumps(result, indent=2))
        return

    if args.command == "generate-sample":
        written = generate_sample_dataset(args.output, count=args.count)
        print(json.dumps({"written": written, "output": str(args.output)}, indent=2))
        return

    if args.command == "analyze":
        summary = analyze_dataset(
            args.input,
            args.output,
            window_minutes=args.window_minutes,
        )
        vectors = export_hashed_vectors(args.input, args.output / "vectors")
        plot_signal_series(args.output / "signals_15m.csv", args.output / "signals.png")
        print(json.dumps({"summary": summary, "vectors": vectors}, indent=2))


if __name__ == "__main__":
    main()
