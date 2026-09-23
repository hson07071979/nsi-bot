# archive/

One-off research scripts that **no longer run against the current engine** or
answer a question that is already settled. Kept for history; results produced by
them are NOT current evidence (see `evidence/*` `meta.status`).

| file | why archived (audit 23/09/2026) |
|---|---|
| `ab_nan.py` | A/B for the NaN total-cap bug (fixed 18/09). Crashes on the current `produce2` output schema (`KeyError: 'metrics'`). The regression is now covered by `tests/test_regressions.py::test_nan_total_cap`. |
