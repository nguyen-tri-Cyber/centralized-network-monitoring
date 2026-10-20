"""
Command-line interface for the anomaly detection module.
Allows users to evaluate metrics from a Prometheus endpoint or synthetic input.
"""

import argparse
import sys
import time
from typing import List, Tuple

from .client import PrometheusClient
from .detector import RollingZScoreDetector, EWMADetector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run statistical anomaly detection on Prometheus time-series metrics."
    )
    parser.add_argument(
        "--prometheus-url",
        default="http://localhost:9090",
        help="Base URL of Prometheus server (default: http://localhost:9090)"
    )
    parser.add_argument(
        "--query",
        default='rate(ifHCInOctets{job="snmp"}[1m]) * 8',
        help="PromQL query expression to evaluate"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=900,
        help="Time window in seconds to inspect backwards from now (default: 900s = 15m)"
    )
    parser.add_argument(
        "--step",
        default="15s",
        help="Query resolution step (default: 15s)"
    )
    parser.add_argument(
        "--algorithm",
        choices=["zscore", "ewma"],
        default="zscore",
        help="Anomaly detection algorithm (default: zscore)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=3.0,
        help="Sigma threshold for anomaly flagging (default: 3.0)"
    )
    parser.add_argument(
        "--window",
        type=int,
        default=15,
        help="Sliding window size for z-score (default: 15)"
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.2,
        help="Smoothing parameter alpha for EWMA (default: 0.2)"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = PrometheusClient(base_url=args.prometheus_url)

    now = time.time()
    start_ts = now - args.duration

    print(f"[INFO] Fetching metric '{args.query}' from {args.prometheus_url} ({args.duration}s window)...")

    try:
        series = client.query_range(args.query, start_ts=start_ts, end_ts=now, step=args.step)
    except Exception as e:
        print(f"[ERROR] Query failed: {e}", file=sys.stderr)
        return 1

    if not series:
        print("[WARN] No time-series data points returned by Prometheus for the given query.")
        return 0

    print(f"[INFO] Received {len(series)} data points.")

    if args.algorithm == "zscore":
        detector = RollingZScoreDetector(window_size=args.window, threshold=args.threshold)
    else:
        detector = EWMADetector(alpha=args.alpha, threshold=args.threshold)

    results = detector.detect_series(series)
    anomalies = [r for r in results if r.is_anomaly]

    print("\n--- Detection Summary ---")
    print(f"Algorithm:       {args.algorithm.upper()}")
    print(f"Total points:    {len(results)}")
    print(f"Anomalies found: {len(anomalies)}")

    if anomalies:
        print("\nFlagged Anomalies:")
        print(f"{'Timestamp':<22} {'Observed':<14} {'Expected':<14} {'Z-Score':<10} {'Type'}")
        print("-" * 70)
        for a in anomalies:
            ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(a.timestamp))
            print(f"{ts_str:<22} {a.value:<14.2f} {a.expected:<14.2f} {a.score:<10.2f} {a.direction}")
    else:
        print("[OK] All data points fall within the normal statistical threshold.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
