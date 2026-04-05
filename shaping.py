"""
rewards/shaping.py — Dedicated reward shaping module.

Provides dense per-step reward signals across three dimensions:
  1. Investigative quality  — are you looking in the right places?
  2. Time-to-detect         — faster correct conclusions = higher reward
  3. Action efficiency      — penalise thrashing, reward progressive narrowing
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# SLA thresholds (seconds) — mirrors real-world incident SLAs
# ---------------------------------------------------------------------------

SLA = {
    "time_to_acknowledge_s":   300,   # 5 min
    "time_to_investigate_s":   900,   # 15 min
    "time_to_resolve_s":      3600,   # 1 hour  (SEV-1)
}

# Max reward attainable from step rewards over a full episode
MAX_STEP_REWARD = 0.15


def shape_reward(
    action_type: str,
    payload: Dict[str, Any],
    ground_truth: Dict[str, Any],
    step: int,
    max_steps: int,
    elapsed_seconds: int,
    action_history: List[str],
) -> tuple[float, Dict[str, Any]]:
    """
    Compute the shaped per-step reward and a breakdown dict.

    Returns:
        (reward: float in [0.0, 0.15], breakdown: dict)
    """
    reward = 0.0
    breakdown: Dict[str, Any] = {"action_type": action_type, "components": {}}

    root_svc = ground_truth.get("root_cause_service", "").lower()
    blast = {s.lower() for s in ground_truth.get("blast_radius", [])}
    rc_alert_id = ground_truth.get("root_cause_alert_id", "")

    # ------------------------------------------------------------------
    # 1. Acknowledgement speed bonus
    # ------------------------------------------------------------------
    if action_type == "acknowledge":
        if elapsed_seconds < SLA["time_to_acknowledge_s"]:
            # Linear decay from 0.08 at t=0 to 0.01 at SLA boundary
            ratio = 1.0 - (elapsed_seconds / SLA["time_to_acknowledge_s"])
            ack_bonus = 0.01 + 0.07 * ratio
        else:
            ack_bonus = 0.0  # Too late — no bonus
        reward += ack_bonus
        breakdown["components"]["ack_speed"] = round(ack_bonus, 4)

    # ------------------------------------------------------------------
    # 2. Log query quality
    # ------------------------------------------------------------------
    elif action_type == "query_logs":
        queried_svc = payload.get("service", "").lower()

        # Penalise duplicate queries (thrashing)
        prior_queries = [h for h in action_history if "query_logs" in h and queried_svc in h]
        if len(prior_queries) >= 2:
            reward -= 0.03  # Already queried this service twice — stop
            breakdown["components"]["duplicate_penalty"] = -0.03
        elif queried_svc == root_svc:
            reward += 0.08   # Queried root cause service
            breakdown["components"]["root_svc_query"] = 0.08
        elif queried_svc in blast:
            reward += 0.03   # Queried a blast-radius service (relevant but not root)
            breakdown["components"]["blast_svc_query"] = 0.03
        else:
            reward += 0.005  # Queried irrelevant service — tiny signal
            breakdown["components"]["irrelevant_query"] = 0.005

        # Bonus for filtering by ERROR/CRITICAL level (good investigation hygiene)
        if payload.get("filter_level", "").upper() in ("ERROR", "CRITICAL", "FATAL"):
            reward += 0.01
            breakdown["components"]["error_filter_bonus"] = 0.01

    # ------------------------------------------------------------------
    # 3. Alert classification quality (intermediate step, not terminal)
    # ------------------------------------------------------------------
    elif action_type == "acknowledge" and payload.get("alert_id"):
        alert_id = payload.get("alert_id", "")
        if alert_id == rc_alert_id:
            reward += 0.05  # Acknowledged root cause alert specifically
            breakdown["components"]["rc_alert_ack"] = 0.05

    # ------------------------------------------------------------------
    # 4. Escalation quality
    # ------------------------------------------------------------------
    elif action_type == "escalate":
        # Escalating before investigating is a red flag
        query_count = sum(1 for h in action_history if "query_logs" in h)
        if query_count < 2:
            reward -= 0.04   # Escalated without investigating
            breakdown["components"]["premature_escalation"] = -0.04
        else:
            severity = payload.get("severity", "").lower()
            # Correct severity escalation
            if severity in ("critical", "high") and ground_truth.get("is_sev1", True):
                reward += 0.03
                breakdown["components"]["correct_escalation_severity"] = 0.03
            # Escalating to the right team
            to_team = payload.get("to_team", "").lower()
            if root_svc.replace("-", "") in to_team.replace("-", "") or \
               any(w in to_team for w in ["database", "network", "platform", "sre"]):
                reward += 0.02
                breakdown["components"]["correct_team"] = 0.02

    # ------------------------------------------------------------------
    # 5. Time pressure: gentle decay as steps accumulate
    #    (incentivises efficient investigation, not brute-force querying)
    # ------------------------------------------------------------------
    step_ratio = step / max_steps
    time_penalty = -0.008 * step_ratio
    reward += time_penalty
    breakdown["components"]["time_pressure"] = round(time_penalty, 4)

    # ------------------------------------------------------------------
    # 6. SLA breach penalty
    # ------------------------------------------------------------------
    if elapsed_seconds > SLA["time_to_investigate_s"]:
        sla_penalty = -0.02
        reward += sla_penalty
        breakdown["components"]["sla_breach"] = sla_penalty

    # Clamp
    reward = max(0.0, min(MAX_STEP_REWARD, reward))
    breakdown["total"] = round(reward, 4)
    return reward, breakdown


def compute_trajectory_bonus(
    rewards: List[float],
    final_score: float,
    steps_taken: int,
    max_steps: int,
    success: bool,
) -> float:
    """
    Compute an end-of-episode trajectory bonus.

    Rewards episodes that:
    - Succeed with fewer steps (efficiency)
    - Have low variance in step rewards (consistent investigation)
    - Score above the success threshold by a margin
    """
    if not success or not rewards:
        return 0.0

    # Efficiency bonus: solved with fewer steps
    efficiency = 1.0 - (steps_taken / max_steps)
    efficiency_bonus = 0.05 * efficiency

    # Score margin bonus (extra for scoring well above threshold)
    margin = max(0.0, final_score - 0.6)
    margin_bonus = min(0.05, margin * 0.25)

    return round(efficiency_bonus + margin_bonus, 4)
