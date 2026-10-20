# Anomaly Detection Module for Prometheus Metrics

## 1. Overview

This module provides a lightweight, explainable statistical anomaly detection engine designed to identify atypical network traffic patterns (spikes, drops, or bandwidth saturation) by querying the Prometheus HTTP API (`/api/v1/query_range`).

Unlike black-box deep learning architectures, statistical methods provide direct traceability: every anomaly is explained by an explicit variance score ($z$-score or EWMA residual standard score) relative to a dynamic local baseline.

---

## 2. Algorithms & Mathematical Formulation

### 2.1 Rolling Z-Score Detector

The **Rolling Z-Score** method maintains a sliding window of historical observations $W = \{x_{t-w+1}, \dots, x_t\}$ of size $w$.

1. **Rolling Mean**:
   $$\mu_t = \frac{1}{|W|} \sum_{i \in W} x_i$$

2. **Rolling Standard Deviation**:
   $$\sigma_t = \sqrt{\frac{1}{|W|-1} \sum_{i \in W} (x_i - \mu_t)^2}$$

3. **Standard Score**:
   $$z_t = \frac{x_t - \mu_{t-1}}{\sigma_{t-1} + \epsilon}$$
   where $\epsilon = 10^{-6}$ is a numerical stabilizer preventing division by zero during flatline traffic periods.

4. **Anomaly Condition**:
   $$\text{Anomaly}(x_t) = \begin{cases} \text{True}, & |z_t| \ge \theta \\ \text{False}, & |z_t| < \theta \end{cases}$$
   where default threshold $\theta = 3.0$ (corresponding to $99.73\%$ confidence under normal distribution assumptions).

### 2.2 Exponentially Weighted Moving Average (EWMA) Detector

The **EWMA** detector applies an exponential weighting factor $\alpha \in (0, 1]$ that places higher weight on recent samples while smoothly discounting older history.

1. **Mean Update**:
   $$\hat{\mu}_t = \alpha x_t + (1 - \alpha) \hat{\mu}_{t-1}$$

2. **Variance Update**:
   $$\hat{\sigma}^2_t = (1 - \alpha) \left( \hat{\sigma}^2_{t-1} + \alpha (x_t - \hat{\mu}_{t-1})^2 \right)$$

3. **Score & Detection**:
   $$s_t = \frac{x_t - \hat{\mu}_{t-1}}{\hat{\sigma}_{t-1} + \epsilon}$$
   Flagged if $|s_t| \ge \theta$.

---

## 3. Assumptions and Prerequisites

1. **Locally Stationary Variance**: The algorithms assume that within the sliding window $w$ (e.g., 15 intervals), the metric exhibits relatively stationary mean and variance.
2. **Near-Gaussian Residuals**: Deviations from the local mean are assumed to roughly approximate a normal distribution.
3. **Sequential Regularity**: Samples are expected at uniform scrape intervals (e.g., every 15 seconds).

---

## 4. Technical Limitations & Trade-offs

1. **Outlier Masking / Adaptation**: If a sustained high-traffic condition persists for several window cycles, the rolling mean and variance will adjust upward, causing subsequent points to no longer be flagged as anomalies.
2. **Seasonal Insensitivity**: Neither rolling Z-score nor EWMA explicitly models multi-scale periodic patterns (e.g., daily business hours vs. weekend quiet hours) without external seasonal decomposition (such as STL or Fourier-based preprocessing).
3. **Parameter Sensitivity**: Performance depends on setting appropriate values for window size $w$, smoothing factor $\alpha$, and threshold $\theta$. A window that is too small leads to false alarms on transient bursts; a window that is too large delays adaptation to structural baseline shifts.
4. **Noise Amplification on Low-Rate Links**: On low-throughput interfaces (e.g., management links carrying a few packets per minute), variance is discrete, which can cause elevated false-alarm rates unless minimum variance floors or packet rate thresholds are applied.

---

## 5. Usage Example

```bash
# Evaluate network traffic over the last 15 minutes
python -m src.anomaly_detector.cli \
  --prometheus-url http://localhost:9090 \
  --query 'rate(ifHCInOctets{job="snmp"}[1m]) * 8' \
  --algorithm zscore \
  --threshold 3.0 \
  --window 15
```
