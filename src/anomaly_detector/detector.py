"""
Time-series anomaly detection algorithms using Rolling Z-Score and EWMA.
Designed with pure Python standard library for zero-dependency execution.
"""

from dataclasses import dataclass
import math
from typing import List, Optional, Tuple, Deque
from collections import deque


@dataclass
class AnomalyResult:
    """Represents the detection assessment for a single metric point."""
    timestamp: float
    value: float
    expected: Optional[float]
    score: float
    is_anomaly: bool
    direction: str  # "spike", "drop", or "normal"


class RollingZScoreDetector:
    """
    Detects anomalies by comparing a point to the rolling mean and standard deviation
    over a fixed sliding window.

    Z = (x - mean) / (std + epsilon)
    """

    def __init__(
        self,
        window_size: int = 15,
        threshold: float = 3.0,
        min_periods: int = 5,
        epsilon: float = 1e-6,
    ):
        if window_size < 2:
            raise ValueError("window_size must be at least 2")
        if threshold <= 0:
            raise ValueError("threshold must be positive")
        if min_periods > window_size:
            raise ValueError("min_periods cannot exceed window_size")

        self.window_size = window_size
        self.threshold = threshold
        self.min_periods = min_periods
        self.epsilon = epsilon
        self.history: Deque[float] = deque(maxlen=window_size)

    def reset(self) -> None:
        """Clears the sliding window history."""
        self.history.clear()

    def detect_point(self, timestamp: float, value: float) -> AnomalyResult:
        """Evaluates a single point against the current sliding window."""
        if len(self.history) < self.min_periods:
            self.history.append(value)
            return AnomalyResult(
                timestamp=timestamp,
                value=value,
                expected=value,
                score=0.0,
                is_anomaly=False,
                direction="normal",
            )

        n = len(self.history)
        mean = sum(self.history) / n
        variance = sum((x - mean) ** 2 for x in self.history) / (n - 1 if n > 1 else 1)
        std = math.sqrt(variance)

        # Standard score calculation with numerical stability guard
        score = (value - mean) / (std + self.epsilon)
        is_anomaly = abs(score) >= self.threshold

        if is_anomaly:
            direction = "spike" if score > 0 else "drop"
        else:
            direction = "normal"

        # Update sliding window with current value
        self.history.append(value)

        return AnomalyResult(
            timestamp=timestamp,
            value=value,
            expected=mean,
            score=score,
            is_anomaly=is_anomaly,
            direction=direction,
        )

    def detect_series(self, series: List[Tuple[float, float]]) -> List[AnomalyResult]:
        """Evaluates an ordered list of (timestamp, value) tuples."""
        self.reset()
        results = []
        for ts, val in series:
            results.append(self.detect_point(ts, val))
        return results


class EWMADetector:
    """
    Exponentially Weighted Moving Average (EWMA) anomaly detector.
    Adapts faster to legitimate shifts while providing dynamic variance bounds.
    """

    def __init__(
        self,
        alpha: float = 0.2,
        threshold: float = 3.0,
        min_periods: int = 3,
        epsilon: float = 1e-6,
    ):
        if not (0.0 < alpha <= 1.0):
            raise ValueError("alpha must be in the range (0.0, 1.0]")
        if threshold <= 0:
            raise ValueError("threshold must be positive")

        self.alpha = alpha
        self.threshold = threshold
        self.min_periods = min_periods
        self.epsilon = epsilon
        self.count = 0
        self.mean: Optional[float] = None
        self.variance: float = 0.0

    def reset(self) -> None:
        """Resets the moving state."""
        self.count = 0
        self.mean = None
        self.variance = 0.0

    def detect_point(self, timestamp: float, value: float) -> AnomalyResult:
        """Evaluates a single point using online EWMA update equations."""
        self.count += 1

        if self.mean is None:
            self.mean = value
            self.variance = 0.0
            return AnomalyResult(
                timestamp=timestamp,
                value=value,
                expected=value,
                score=0.0,
                is_anomaly=False,
                direction="normal",
            )

        expected = self.mean
        diff = value - expected
        std = math.sqrt(self.variance)
        score = diff / (std + self.epsilon)

        if self.count < self.min_periods:
            is_anomaly = False
            direction = "normal"
        else:
            is_anomaly = abs(score) >= self.threshold
            direction = "spike" if score > 0 else "drop" if is_anomaly else "normal"

        # Online update of EWMA mean and variance
        self.mean = expected + self.alpha * diff
        self.variance = (1.0 - self.alpha) * (self.variance + self.alpha * (diff ** 2))

        return AnomalyResult(
            timestamp=timestamp,
            value=value,
            expected=expected,
            score=score,
            is_anomaly=is_anomaly,
            direction=direction,
        )

    def detect_series(self, series: List[Tuple[float, float]]) -> List[AnomalyResult]:
        """Evaluates an ordered list of (timestamp, value) tuples."""
        self.reset()
        results = []
        for ts, val in series:
            results.append(self.detect_point(ts, val))
        return results
