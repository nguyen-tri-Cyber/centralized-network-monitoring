"""
Anomaly Detection Module for Network Observability.

Provides explainable, lightweight time-series anomaly detection algorithms
(Rolling Z-Score and Exponentially Weighted Moving Average) for Prometheus metrics.
"""

from .detector import (
    AnomalyResult,
    RollingZScoreDetector,
    EWMADetector,
)
from .client import PrometheusClient

__all__ = [
    "AnomalyResult",
    "RollingZScoreDetector",
    "EWMADetector",
    "PrometheusClient",
]
