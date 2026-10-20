"""
Unit tests for the Anomaly Detection Module.
Evaluates Rolling Z-Score, EWMA, and Prometheus client parsing using synthetic time-series data.
"""

import unittest
from unittest.mock import patch, MagicMock
import io
import json
import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.anomaly_detector.detector import RollingZScoreDetector, EWMADetector
from src.anomaly_detector.client import PrometheusClient



class TestRollingZScoreDetector(unittest.TestCase):
    def setUp(self):
        self.detector = RollingZScoreDetector(window_size=10, threshold=3.0, min_periods=5)

    def test_invalid_parameters_raise(self):
        with self.assertRaises(ValueError):
            RollingZScoreDetector(window_size=1)
        with self.assertRaises(ValueError):
            RollingZScoreDetector(threshold=-1.0)
        with self.assertRaises(ValueError):
            RollingZScoreDetector(window_size=5, min_periods=10)

    def test_flatline_zero_variance_does_not_crash(self):
        """Constant values have std=0. Epsilon should prevent ZeroDivisionError."""
        series = [(float(i), 100.0) for i in range(20)]
        results = self.detector.detect_series(series)
        self.assertEqual(len(results), 20)
        for r in results:
            self.assertFalse(r.is_anomaly)
            self.assertEqual(r.score, 0.0)

    def test_normal_baseline_has_no_anomalies(self):
        """Stable series with minor variations should yield zero anomalies at 3-sigma."""
        # Baseline with alternating minor variation (+1, -1)
        series = [(float(i), 100.0 + (1.0 if i % 2 == 0 else -1.0)) for i in range(30)]
        results = self.detector.detect_series(series)
        anomalies = [r for r in results if r.is_anomaly]
        self.assertEqual(len(anomalies), 0)

    def test_single_sharp_spike_is_detected(self):
        """A sudden extreme spike above baseline must be flagged with direction 'spike'."""
        series = [(float(i), 50.0 + (0.5 if i % 2 == 0 else -0.5)) for i in range(20)]
        # Inject spike at step 20
        series.append((20.0, 500.0))
        # Resume baseline
        series.extend([(float(i), 50.0) for i in range(21, 30)])

        results = self.detector.detect_series(series)
        spike_result = results[20]

        self.assertTrue(spike_result.is_anomaly)
        self.assertEqual(spike_result.direction, "spike")
        self.assertGreater(spike_result.score, 3.0)

    def test_sudden_drop_is_detected(self):
        """A sudden drop from a high baseline must be flagged with direction 'drop'."""
        series = [(float(i), 1000.0 + (5.0 if i % 2 == 0 else -5.0)) for i in range(20)]
        # Inject sudden drop
        series.append((20.0, 10.0))

        results = self.detector.detect_series(series)
        drop_result = results[20]

        self.assertTrue(drop_result.is_anomaly)
        self.assertEqual(drop_result.direction, "drop")
        self.assertLess(drop_result.score, -3.0)

    def test_insufficient_samples_flag_nothing(self):
        """Periods before min_periods should never flag anomalies."""
        series = [(float(i), 1000.0 * (i + 1)) for i in range(4)]
        results = self.detector.detect_series(series)
        for r in results:
            self.assertFalse(r.is_anomaly)


class TestEWMADetector(unittest.TestCase):
    def setUp(self):
        self.detector = EWMADetector(alpha=0.3, threshold=3.0, min_periods=4)

    def test_invalid_parameters_raise(self):
        with self.assertRaises(ValueError):
            EWMADetector(alpha=0.0)
        with self.assertRaises(ValueError):
            EWMADetector(alpha=1.5)
        with self.assertRaises(ValueError):
            EWMADetector(threshold=0.0)

    def test_stable_series_produces_no_anomalies(self):
        series = [(float(i), 200.0 + (2.0 if i % 2 == 0 else -2.0)) for i in range(25)]
        results = self.detector.detect_series(series)
        anomalies = [r for r in results if r.is_anomaly]
        self.assertEqual(len(anomalies), 0)

    def test_ewma_spike_detection(self):
        series = [(float(i), 100.0) for i in range(15)]
        # Add slight natural jitter to build baseline variance
        for i in range(15):
            series[i] = (float(i), 100.0 + (1.0 if i % 2 == 0 else -1.0))
        series.append((15.0, 800.0))

        results = self.detector.detect_series(series)
        spike_point = results[15]
        self.assertTrue(spike_point.is_anomaly)
        self.assertEqual(spike_point.direction, "spike")


class TestPrometheusClient(unittest.TestCase):
    def setUp(self):
        self.client = PrometheusClient(base_url="http://mock-prometheus:9090")

    @patch("urllib.request.urlopen")
    def test_query_range_success(self, mock_urlopen):
        mock_response = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"instance": "snmp-simulator:161", "job": "snmp"},
                        "values": [
                            [1700000000, "1048576"],
                            [1700000015, "2097152"],
                            [1700000030, "3145728"]
                        ]
                    }
                ]
            }
        }
        mock_cm = MagicMock()
        mock_cm.read.return_value = json.dumps(mock_response).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_cm

        series = self.client.query_range("rate(ifHCInOctets[1m])", 1700000000, 1700000030)
        self.assertEqual(len(series), 3)
        self.assertEqual(series[0], (1700000000.0, 1048576.0))
        self.assertEqual(series[2], (1700000030.0, 3145728.0))

    @patch("urllib.request.urlopen")
    def test_query_api_error_raises_runtime_error(self, mock_urlopen):
        mock_response = {
            "status": "error",
            "errorType": "bad_data",
            "error": "parse error at char 1"
        }
        mock_cm = MagicMock()
        mock_cm.read.return_value = json.dumps(mock_response).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_cm

        with self.assertRaises(RuntimeError) as ctx:
            self.client.query_instant("invalid_syntax{{{")
        self.assertIn("Prometheus query failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
