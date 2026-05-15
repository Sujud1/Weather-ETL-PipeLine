"""
pipeline.py
-----------
ETL Pipeline Orchestrator
Runs all 4 steps in sequence: Extract -> Transform -> Load -> Visualize

Usage:
    python pipeline.py              # run full pipeline
    python pipeline.py --step 1     # run only extract
    python pipeline.py --step 2     # run only transform
    python pipeline.py --step 3     # run only load
    python pipeline.py --step 4     # run only visualize

Author: Sujud Alatrash
"""

import argparse
import time
from datetime import datetime

from extract   import extract
from transform import transform
from load      import load
from dashboard import visualize


def run_pipeline():
    """Run all 4 ETL steps and report total time."""
    start = time.time()

    print("\n" + "=" * 50)
    print("  WEATHER ETL PIPELINE")
    print(f"  Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 50 + "\n")

    raw_file       = extract()   ; print()
    df, clean_file = transform() ; print()
    rows           = load()      ; print()
    dashboard_path = visualize() ; print()

    elapsed = time.time() - start
    print("=" * 50)
    print(f"  PIPELINE COMPLETE  ({elapsed:.1f}s)")
    print(f"  Rows loaded  : {rows}")
    print(f"  Dashboard    : {dashboard_path}")
    print("=" * 50 + "\n")


def run_step(step: int):
    """Run a single step by number."""
    steps = {
        1: lambda: extract(),
        2: lambda: transform(),
        3: lambda: load(),
        4: lambda: visualize(),
    }
    if step not in steps:
        raise ValueError(f"Invalid step: {step}. Choose 1-4.")
    steps[step]()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weather ETL Pipeline")
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4],
                        help="Run a single step (1=Extract 2=Transform 3=Load 4=Visualize)")
    args = parser.parse_args()

    if args.step:
        run_step(args.step)
    else:
        run_pipeline()