# PreferredMaxLatency

Preferred maximum latency (in seconds). Can be a number (applies to p50) or an object with percentile-specific cutoffs. Endpoints above the threshold(s) may still be used, but are deprioritized in routing. When using fallback models, this may cause a fallback model to be used instead of the primary model if it meets the threshold.


## Supported Types

### `float`

```python
value: float = /* values here */
```

### `components.PercentileLatencyCutoffs`

```python
value: components.PercentileLatencyCutoffs = /* values here */
```

### `Any`

```python
value: Any = /* values here */
```

