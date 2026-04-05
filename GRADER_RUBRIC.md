# Grader Rubric

Full scoring criteria for all three tasks. This document is for human reviewers in Phase 3.

---

## Task 1 — Alert Classification

**Total weight: 100%**

### Root cause identified (40%)

| Score | Criterion |
|---|---|
| 1.00 | Correct `root_cause_alert_id` AND correct `root_cause_service` |
| 0.50 | Correct `root_cause_service` only (alert ID wrong) |
| 0.25 | Correct `root_cause_alert_id` only (service name wrong) |
| 0.00 | Both wrong |

**Rationale:** Identifying the root cause alert is the primary skill being tested. Partial credit for getting the service right even if the specific alert ID is wrong — service is the more important signal for downstream remediation.

---

### Severity assignments (30%)

Score = `(number of correctly assigned alerts) / (total alerts)`

Each alert must be assigned one of: `critical`, `high`, `medium`, `low`, `info`.

Ground truth severity is determined by:
- `critical` — alert on the root cause service, or a direct dependency that is fully down
- `high` — alert on a service with >30% error rate or direct cascade from root cause
- `medium` — alert on indirectly affected services
- `low` — alert on peripheral services (queues backing up, auxiliary degradation)

No partial credit per alert — each is either right or wrong.

---

### Blast radius (20%)

Score = `(correctly named services) / (total expected blast radius services)`

Minus `0.05` per false positive (service incorrectly included in blast radius), minimum 0.

**What counts as blast radius:** Any service that is **actively degraded** due to the root cause, not just any service in the topology. A service that has retry logic absorbing the failure without user-visible impact should not be in the blast radius.

---

### Reasoning quality (10%)

Score = `min(1.0, word_count / 30)`

Requires at least a 30-word explanation. Any coherent sentence mentioning timestamps, topology, or log evidence qualifies. This criterion is intentionally lenient — it rewards agents that provide *any* reasoning over agents that just output structured data with no explanation.

---

## Task 2 — Root Cause Analysis

**Total weight: 100%**

### Root cause service (35%)

| Score | Criterion |
|---|---|
| 1.00 | Exact match (case-insensitive, substring match allowed e.g. "postgres" matches "postgres-primary") |
| 0.00 | Wrong service |

No partial credit — the fundamental question is whether the agent identified the right service.

---

### Causal chain accuracy (30%)

Score combines:
- **70%** keyword coverage: fraction of important words from the expected causal chain found in the agent's chain
- **30%** step count ratio: `min(agent_steps, expected_steps) / expected_steps`

Keywords extracted: top 3 meaningful words (>4 chars) from each expected chain step.

**Example:** Expected chain step: `"ML training job requests 28Gi on 32Gi node"` → keywords: `["training", "requests", "28Gi"]`

**Why keyword coverage?** Full semantic similarity requires an LLM at eval time, breaking reproducibility. Keyword coverage over a carefully curated set is a deterministic proxy that captures whether the agent traced the right failure mechanism.

---

### Contributing factors (20%)

Same keyword coverage approach as causal chain, applied to contributing factors.

Expected contributing factors are conditions that:
1. Made the incident more likely to occur
2. Made it worse once it started
3. Made it harder to detect or remediate

**Good contributing factor:** "ML training job had no memory resource limits in its Kubernetes spec"
**Poor contributing factor:** "The system failed" (too vague, no actionability)

---

### Description quality (15%)

Combines:
- **70%** keyword coverage against expected description
- **30%** minimum 20-word length check

Rewards precise, specific technical descriptions over vague summaries.

---

## Task 3 — Post-Mortem Writing

**Total weight: 100%**

### Section completeness (25%)

Required sections: `impact_summary`, `timeline`, `root_cause`, `contributing_factors`, `action_items`, `lessons_learned`

Score = `present_sections / 6`

A section is "present" if:
- String fields: length > 10 characters
- List fields: at least 1 item

---

### Root cause accuracy (25%)

Keyword coverage of `expected_root_cause_keywords` in the `root_cause` field.

These keywords are carefully chosen to be the technical terms that distinguish this root cause from a generic failure description. An agent that writes "the database failed" for a cert expiry incident scores 0; an agent that mentions "TTL", "nameserver", "Route53", "propagation" scores high.

---

### Action item quality (20%)

Three components:

**Count (40%):** `min(1.0, actual_count / minimum_required)`

**Structural quality (30%):** Fraction of items that have both `owner` and `due_date` populated. An action item without an owner is not actionable.

**Theme coverage (30%):** Keyword coverage of `required_action_item_themes`. These themes are the categories of improvement the post-mortem should identify — e.g. for a cert expiry incident: `["ttl validation", "propagation check", "runbook", "rollback plan"]`

**What makes a good action item:**
- Specific: "Add lock_timeout=30s to all production migration scripts" not "improve database safety"
- Owned: has a team or individual name
- Time-bounded: has a due date within 30 days
- Theme-covering: addresses one of the systemic failure patterns

---

### Timeline completeness (15%)

Two components:
- **60%** event count vs minimum (`min(1.0, actual / minimum)`)
- **40%** structural quality: fraction of events with both `time` and `event` fields

Minimum event counts per scenario are set to capture the key inflection points: detection, acknowledgement, investigation, mitigation, resolution.

---

### Contributing factors (15%)

Same keyword coverage approach as Task 2. Contributing factors in post-mortems should address *why the incident happened* (root cause enablers) rather than just describing what happened.

---

## Reward shaping (per-step)

Dense per-step rewards supplement the final graded score:

| Action | Reward |
|---|---|
| `acknowledge` within SLA (5 min) | +0.01 to +0.08 (linear decay) |
| `query_logs` on root cause service | +0.08 |
| `query_logs` on blast-radius service | +0.03 |
| `query_logs` on irrelevant service | +0.005 |
| `query_logs` with `filter_level=ERROR` | +0.01 bonus |
| `escalate` with <2 prior queries | −0.04 |
| `escalate` with ≥2 prior queries + correct severity | +0.05 |
| Duplicate log query (≥2x same service) | −0.03 |
| SLA breach (>15 min elapsed) | −0.02 |
| Time pressure | −0.008 × (step/max_steps) |

**Final episode reward:** `0.70 × graded_score + 0.30 × mean(step_rewards)`

This ensures agents learn *investigative process*, not just final answers.
