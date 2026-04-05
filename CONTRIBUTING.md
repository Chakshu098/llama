# Contributing

## Adding new scenarios

Scenarios are the lifeblood of the benchmark — the more diverse, the better.

**Quick path:**
1. Read `docs/SCENARIO_SCHEMA.md` for the schema
2. Generate a starting point: `python scripts/generate_scenario.py --task alert-classification --failure redis_oom`
3. Edit the generated dict — add realistic log lines, refine ground truth
4. Validate: `python scripts/validate_scenario.py`
5. Add to the right list in `scenarios.py`
6. Run `make test`

**What makes a great scenario:**
- A real failure mode you've personally seen in production
- At least one misleading alert (a service that looks bad but is a symptom)
- Log timestamps that clearly trace causality
- A non-obvious root cause (can't just pattern-match on alert severity)
- Tight, specific `expected_root_cause_keywords` — not generic words like "failed"

**Failure modes we still need:**
- Network partition (split-brain)
- Disk quota exhaustion (different from disk I/O saturation)
- Rate limiter misconfiguration
- Service mesh sidecar crash (Envoy/Istio)
- Cascading retry storm (retry amplification)
- Config map hot-reload failure

## Improving graders

Graders live in `graders.py`. Each is a standalone class with a `grade(response) → (score, breakdown)` method.

If you find a case where an obviously correct answer scores low, or an obviously wrong answer scores high:
1. Write a failing test in `tests/test_graders.py` that reproduces the problem
2. Fix the grader
3. Confirm the test passes and no other tests break

## Running the eval suite

```bash
# Start server
make run &

# Run full eval (oracle + random agents across all scenarios)
python eval/run_eval.py --episodes 3

# Outputs eval/score_report.json
```

The eval report shows:
- `oracle_avg_score` — ceiling score (correct answers)
- `random_avg_score` — floor score (random guessing)
- `discriminability` — oracle minus random (should be > 0.40 per task)

If discriminability is low on a task, the grader needs tuning.

## Code style

- Python 3.10+
- Pydantic v2
- Line length ≤ 100 chars (`ruff check` enforces this)
- All new modules need `__init__.py`
- All new grader criteria need a corresponding test

## Running tests

```bash
make test           # all tests
make test-unit      # graders + environment only (fast)
make test-integration  # HTTP server tests (slower)
```
