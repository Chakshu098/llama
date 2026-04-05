# Scenario Schema

How to write a new scenario and add it to the benchmark.

---

## Quick start

1. Copy a scenario from `scenarios.py` that matches your target task
2. Change the `id`, `description`, and all data fields
3. Run `python scripts/validate_scenario.py` to check it
4. Run the full test suite: `make test`

---

## Alert Classification scenario

```python
{
    "id": "sc-ac-XXX",                         # unique, no spaces
    "description": "Short description of the failure pattern",
    "alerts": [
        {
            "alert_id":     "ALT-001",          # unique within scenario
            "service":      "postgres-primary", # service name (matches topology key)
            "severity":     "critical",         # critical | high | medium | low | info
            "is_root_cause": True,              # exactly ONE alert must be True
            "message":      "Human-readable alert text",
            "timestamp":    "2024-03-15T14:31:47Z",   # ISO 8601 UTC
            "tags":         {"env": "prod"}     # optional k/v tags
        },
        # ... more alerts (5-8 recommended)
    ],
    "logs": [
        {
            "timestamp":  "2024-03-15T14:31:45Z",
            "service":    "postgres-primary",
            "level":      "ERROR",              # ERROR | WARN | INFO | DEBUG
            "message":    "Log line text",
            "trace_id":   None                  # or "trace-abc123"
        },
        # ... 3-8 log lines (include root cause service logs first)
    ],
    "topology": {
        "services": {
            "postgres-primary": {
                "upstream":   [],                        # services this depends on
                "downstream": ["payment-service"],       # services depending on this
                "healthy":    False                      # False = degraded in this scenario
            },
            # ... all services referenced in alerts
        }
    },
    "ground_truth": {
        "root_cause_alert_id":   "ALT-002",             # must match an alert_id
        "root_cause_service":    "postgres-primary",    # must match a topology key
        "blast_radius":          ["payment-service", "checkout-api"],  # affected services
        "correct_severity_map":  {                      # alert_id → correct severity
            "ALT-001": "critical",
            "ALT-002": "critical",
            "ALT-003": "high",
        }
    }
}
```

### Design tips
- Timestamps matter: root cause alert should fire **before** downstream alerts (10-90 seconds earlier)
- Include at least 1 misleading alert — a service that looks bad but is actually a symptom
- Topology upstream/downstream must be consistent (if A depends on B, B is upstream of A)
- 5-8 alerts is the sweet spot: enough complexity, not overwhelming

---

## Root Cause Analysis scenario

Same structure as Alert Classification, plus richer `ground_truth`:

```python
"ground_truth": {
    "root_cause_alert_id":    "ALT-203",
    "root_cause_service":     "k8s-node-07",
    "root_cause_description": "Precise 2-4 sentence technical description of what happened and why",
    "causal_chain": [
        "Step 1: what triggered the failure",
        "Step 2: what that caused",
        "Step 3: how it cascaded",
        # ... 4-8 steps, each logically following the last
    ],
    "contributing_factors": [
        "Condition that made the failure more likely",
        "Condition that made it worse or harder to detect",
        # ... 2-4 factors
    ]
}
```

### Design tips for RCA scenarios
- Logs must contain the causal chain — the agent should be able to trace it from timestamps
- Introduce at least 2 hops: A caused B which caused C (not just A caused C)
- Make the root cause non-obvious from alerts alone — require log reading
- Include a "red herring" service that has high error rates but is downstream of the real root cause

---

## Post-Mortem scenario

```python
{
    "id": "sc-pm-XXX",
    "description": "...",
    "incident_summary": {
        "title":             "Descriptive incident title",
        "duration_minutes":  47,
        "start_time":        "2024-03-15T14:31:47Z",
        "end_time":          "2024-03-15T15:18:52Z",
        "affected_services": ["list", "of", "services"],
        "user_impact":       "Quantified impact: N users, N% requests, $N revenue",
        "severity":          "SEV-1"     # SEV-1 | SEV-2 | SEV-3
    },
    "timeline": [
        {"time": "14:22:00Z", "event": "Description of event"},
        # ... 10-15 events from trigger to resolution
    ],
    "alerts": [ ... ],   # same format as above (already resolved)
    "logs":   [],        # usually empty — post-mortem uses timeline
    "topology": { ... },
    "ground_truth": {
        "required_sections": [
            "impact_summary", "timeline", "root_cause",
            "contributing_factors", "action_items", "lessons_learned"
        ],
        "expected_root_cause_keywords": [
            # 5-10 technical keywords that MUST appear in a correct root cause description
            # e.g. for a cert expiry: ["ttl", "nameserver", "route53", "propagation"]
        ],
        "expected_contributing_factors": [
            "Factor 1 as a short phrase",
            "Factor 2",
            # 3-5 factors
        ],
        "required_action_item_themes": [
            # Categories of improvement — keywords agent's action items should cover
            "ttl validation", "propagation check", "runbook"
        ],
        "minimum_timeline_events": 8,   # minimum events in agent's timeline
        "minimum_action_items":    3    # minimum action items
    }
}
```

### Design tips for postmortem scenarios
- Timeline should tell a clear story with a beginning (trigger), middle (investigation), end (resolution)
- `expected_root_cause_keywords` should be specific technical terms, not generic words
- Action items should map 1:1 to contributing factors — each factor should have at least one action item
- Include the dollar/user impact in `user_impact` — agents that don't mention scope score lower

---

## Validation

After writing a scenario, always run:

```bash
python scripts/validate_scenario.py
```

This checks:
- All required keys present
- Alert IDs in ground truth exist in alerts list
- Severity values are valid
- Graders produce scores in [0.0, 1.0]
- Perfect oracle answers score ≥ 0.80 (alert classification) or ≥ 0.75 (RCA)
