"""
graders.py — Deterministic graders for all three tasks.

Each grader returns a score in [0.0, 1.0] and a breakdown dict
explaining which sub-criteria were met. Scores are reproducible.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from models import ActionType


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _keyword_coverage(text: str, keywords: List[str]) -> float:
    """Return fraction of keywords found (case-insensitive) in text."""
    if not keywords:
        return 1.0
    text_lower = text.lower()
    found = sum(1 for kw in keywords if kw.lower() in text_lower)
    return found / len(keywords)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Task 1 — Alert Classification grader
# ---------------------------------------------------------------------------

class AlertClassificationGrader:
    """
    Scores an agent's alert classification attempt.

    Criteria (weighted):
      40%  Root cause identified correctly
      30%  Severity assignments match ground truth
      20%  Blast radius identified (affected services named)
      10%  At least one supporting reasoning sentence provided
    """

    WEIGHTS = {
        "root_cause": 0.40,
        "severity":   0.30,
        "blast_radius": 0.20,
        "reasoning":  0.10,
    }

    def __init__(self, scenario: Dict[str, Any]):
        self.gt = scenario["ground_truth"]
        self.scenario = scenario

    def grade(self, agent_response: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        agent_response keys expected:
          root_cause_alert_id: str
          root_cause_service:  str
          severity_assignments: dict[alert_id -> severity]
          blast_radius_services: list[str]
          reasoning: str
        """
        breakdown: Dict[str, Any] = {}

        # --- Root cause (40%) ---
        predicted_rc = agent_response.get("root_cause_alert_id", "")
        predicted_svc = agent_response.get("root_cause_service", "")
        rc_id_correct = (predicted_rc == self.gt["root_cause_alert_id"])
        rc_svc_correct = (predicted_svc.lower() == self.gt["root_cause_service"].lower())
        root_cause_score = 1.0 if (rc_id_correct and rc_svc_correct) \
            else 0.5 if rc_svc_correct \
            else 0.25 if rc_id_correct \
            else 0.0
        breakdown["root_cause"] = {
            "score": root_cause_score,
            "alert_id_correct": rc_id_correct,
            "service_correct": rc_svc_correct,
        }

        # --- Severity assignments (30%) ---
        correct_sev = self.gt.get("correct_severity_map", {})
        predicted_sev = agent_response.get("severity_assignments", {})
        if correct_sev:
            matches = sum(
                1 for aid, sev in correct_sev.items()
                if predicted_sev.get(aid, "").lower() == sev.lower()
            )
            sev_score = matches / len(correct_sev)
        else:
            sev_score = 1.0
        breakdown["severity"] = {
            "score": sev_score,
            "correct": sum(1 for a, s in correct_sev.items() if predicted_sev.get(a, "").lower() == s.lower()),
            "total": len(correct_sev),
        }

        # --- Blast radius (20%) ---
        expected_blast = {s.lower() for s in self.gt.get("blast_radius", [])}
        predicted_blast = {s.lower() for s in agent_response.get("blast_radius_services", [])}
        if expected_blast:
            overlap = len(expected_blast & predicted_blast)
            blast_score = overlap / len(expected_blast)
            # Penalise false positives slightly
            fp = len(predicted_blast - expected_blast)
            blast_score = _clamp(blast_score - (fp * 0.05))
        else:
            blast_score = 1.0
        breakdown["blast_radius"] = {
            "score": blast_score,
            "expected": list(expected_blast),
            "predicted": list(predicted_blast),
        }

        # --- Reasoning quality (10%) ---
        reasoning = agent_response.get("reasoning", "")
        reasoning_score = min(1.0, len(reasoning.split()) / 30) if reasoning else 0.0
        breakdown["reasoning"] = {"score": reasoning_score, "word_count": len(reasoning.split())}

        total = sum(
            breakdown[k]["score"] * w for k, w in self.WEIGHTS.items()
        )
        return _clamp(total), breakdown


# ---------------------------------------------------------------------------
# Task 2 — Root Cause Analysis grader
# ---------------------------------------------------------------------------

class RootCauseAnalysisGrader:
    """
    Scores an agent's root cause analysis.

    Criteria (weighted):
      35%  Correct root cause service identified
      30%  Causal chain accuracy (keyword coverage over ground truth chain)
      20%  Contributing factors coverage
      15%  Description quality and specificity
    """

    WEIGHTS = {
        "root_cause_service": 0.35,
        "causal_chain":       0.30,
        "contributing_factors": 0.20,
        "description_quality": 0.15,
    }

    def __init__(self, scenario: Dict[str, Any]):
        self.gt = scenario["ground_truth"]

    def grade(self, agent_response: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        agent_response keys expected:
          root_cause_service:      str
          root_cause_description:  str
          causal_chain:            list[str]
          contributing_factors:    list[str]
        """
        breakdown: Dict[str, Any] = {}

        # --- Root cause service (35%) ---
        predicted_svc = agent_response.get("root_cause_service", "").lower()
        expected_svc = self.gt["root_cause_service"].lower()
        # Allow partial match (service name fragment)
        svc_score = 1.0 if expected_svc in predicted_svc or predicted_svc in expected_svc else 0.0
        breakdown["root_cause_service"] = {"score": svc_score, "expected": expected_svc, "predicted": predicted_svc}

        # --- Causal chain (30%) ---
        expected_chain = self.gt.get("causal_chain", [])
        predicted_chain = agent_response.get("causal_chain", [])
        predicted_chain_text = " ".join(predicted_chain).lower()
        # Extract key terms from each expected chain step
        chain_keywords = []
        for step in expected_chain:
            words = [w for w in step.lower().split() if len(w) > 4]
            chain_keywords.extend(words[:3])  # top 3 meaningful words per step
        chain_score = _keyword_coverage(predicted_chain_text, chain_keywords) if chain_keywords else 0.5
        # Bonus for having roughly right number of steps
        step_ratio = min(len(predicted_chain), len(expected_chain)) / max(len(expected_chain), 1)
        chain_score = _clamp(chain_score * 0.7 + step_ratio * 0.3)
        breakdown["causal_chain"] = {"score": chain_score, "keyword_coverage": _keyword_coverage(predicted_chain_text, chain_keywords)}

        # --- Contributing factors (20%) ---
        expected_factors = self.gt.get("contributing_factors", [])
        predicted_factors_text = " ".join(agent_response.get("contributing_factors", [])).lower()
        factor_keywords = []
        for factor in expected_factors:
            words = [w for w in factor.lower().split() if len(w) > 4]
            factor_keywords.extend(words[:3])
        factor_score = _keyword_coverage(predicted_factors_text, factor_keywords) if factor_keywords else 0.5
        breakdown["contributing_factors"] = {"score": factor_score}

        # --- Description quality (15%) ---
        description = agent_response.get("root_cause_description", "")
        # Check keyword coverage of expected description
        expected_desc_kws = self.gt["root_cause_description"].lower().split()
        expected_desc_kws = [w for w in expected_desc_kws if len(w) > 5][:15]
        desc_coverage = _keyword_coverage(description, expected_desc_kws)
        desc_length_ok = len(description.split()) >= 20
        desc_score = _clamp(desc_coverage * 0.7 + (0.3 if desc_length_ok else 0.0))
        breakdown["description_quality"] = {"score": desc_score, "word_count": len(description.split())}

        total = sum(
            breakdown[k]["score"] * w for k, w in self.WEIGHTS.items()
        )
        return _clamp(total), breakdown


# ---------------------------------------------------------------------------
# Task 3 — Post-Mortem Writing grader
# ---------------------------------------------------------------------------

class PostMortemGrader:
    """
    Scores a written post-mortem document.

    Criteria (weighted):
      25%  Section completeness (all required sections present)
      25%  Root cause accuracy (expected keywords in root_cause field)
      20%  Action item quality (count, has owners, has due dates)
      15%  Timeline completeness (event count vs minimum required)
      15%  Contributing factors coverage
    """

    WEIGHTS = {
        "section_completeness":   0.25,
        "root_cause_accuracy":    0.25,
        "action_item_quality":    0.20,
        "timeline_completeness":  0.15,
        "contributing_factors":   0.15,
    }

    def __init__(self, scenario: Dict[str, Any]):
        self.gt = scenario["ground_truth"]
        self.incident = scenario["incident_summary"]

    def grade(self, agent_response: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        agent_response keys expected (matching WritePostmortemAction):
          title:                str
          impact_summary:       str
          timeline:             list[{time, event}]
          root_cause:           str
          contributing_factors: list[str]
          action_items:         list[{owner, description, due_date}]
          lessons_learned:      str
        """
        breakdown: Dict[str, Any] = {}

        # --- Section completeness (25%) ---
        required = self.gt["required_sections"]
        present = []
        for section in required:
            val = agent_response.get(section)
            if val and (isinstance(val, str) and len(val) > 10) or \
               (isinstance(val, list) and len(val) > 0):
                present.append(section)
        section_score = len(present) / len(required)
        breakdown["section_completeness"] = {"score": section_score, "present": present, "missing": [s for s in required if s not in present]}

        # --- Root cause accuracy (25%) ---
        root_cause_text = agent_response.get("root_cause", "")
        expected_kws = self.gt.get("expected_root_cause_keywords", [])
        rc_score = _keyword_coverage(root_cause_text, expected_kws)
        breakdown["root_cause_accuracy"] = {
            "score": rc_score,
            "keyword_coverage": f"{sum(1 for k in expected_kws if k.lower() in root_cause_text.lower())}/{len(expected_kws)}"
        }

        # --- Action item quality (20%) ---
        action_items = agent_response.get("action_items", [])
        min_items = self.gt.get("minimum_action_items", 3)
        count_score = min(1.0, len(action_items) / min_items)
        # Check for owners and due dates
        has_owner = sum(1 for ai in action_items if ai.get("owner", "").strip())
        has_due = sum(1 for ai in action_items if ai.get("due_date", "").strip())
        quality_score = (has_owner + has_due) / (2 * max(len(action_items), 1)) if action_items else 0.0
        # Check theme coverage
        themes = self.gt.get("required_action_item_themes", [])
        ai_text = " ".join(str(ai) for ai in action_items).lower()
        theme_coverage = _keyword_coverage(ai_text, themes)
        ai_score = _clamp(count_score * 0.4 + quality_score * 0.3 + theme_coverage * 0.3)
        breakdown["action_item_quality"] = {
            "score": ai_score, "count": len(action_items),
            "has_owners": has_owner, "has_due_dates": has_due
        }

        # --- Timeline completeness (15%) ---
        timeline = agent_response.get("timeline", [])
        min_events = self.gt.get("minimum_timeline_events", 6)
        timeline_score = _clamp(len(timeline) / min_events)
        # Bonus: check events have both time and event fields
        well_formed = sum(1 for e in timeline if e.get("time") and e.get("event"))
        if timeline:
            timeline_score = _clamp(timeline_score * 0.6 + (well_formed / len(timeline)) * 0.4)
        breakdown["timeline_completeness"] = {"score": timeline_score, "event_count": len(timeline), "minimum": min_events}

        # --- Contributing factors (15%) ---
        factors = agent_response.get("contributing_factors", [])
        factors_text = " ".join(str(f) for f in factors).lower()
        expected_factors = self.gt.get("expected_contributing_factors", [])
        factor_kws = []
        for f in expected_factors:
            factor_kws.extend([w for w in f.lower().split() if len(w) > 4][:3])
        cf_score = _keyword_coverage(factors_text, factor_kws) if factor_kws else (0.5 if factors else 0.0)
        breakdown["contributing_factors"] = {"score": cf_score, "count": len(factors)}

        total = sum(
            breakdown[k]["score"] * w for k, w in self.WEIGHTS.items()
        )
        return _clamp(total), breakdown


# ---------------------------------------------------------------------------
# Reward shaping — trajectory-level partial rewards
# ---------------------------------------------------------------------------

def compute_step_reward(
    action_type: str,
    action_payload: Dict[str, Any],
    observation_before: Dict[str, Any],
    ground_truth: Dict[str, Any],
    step: int,
    max_steps: int,
) -> float:
    """
    Provide dense per-step reward signal so agents get gradient throughout
    the episode, not just at the end.

    Returns a small float in [0.0, 0.15] per step.
    """
    reward = 0.0

    # Reward for acknowledging alerts early (time-to-acknowledge matters)
    if action_type == "acknowledge":
        # Higher reward for early acknowledgement
        time_factor = 1.0 - (step / max_steps)
        reward += 0.05 * time_factor

    # Reward for querying logs of the right service
    elif action_type == "query_logs":
        queried_service = action_payload.get("service", "").lower()
        root_svc = ground_truth.get("root_cause_service", "").lower()
        if queried_service == root_svc:
            reward += 0.08  # Queried the right service logs
        elif queried_service in ground_truth.get("blast_radius", []):
            reward += 0.03  # At least a relevant service

    # Reward for correct classification
    elif action_type == "classify_alert":
        alert_id = action_payload.get("alert_id", "")
        # Handle the case where is_root_cause might be missing in payload
        is_rc_prediction = action_payload.get("is_root_cause", False)
        is_rc_actual = (alert_id == ground_truth.get("root_cause_alert_id"))
        if is_rc_prediction == is_rc_actual:
            reward += 0.06

    # Reward for remediation actions
    elif action_type == ActionType.RESTART_SERVICE:
        reward += 0.02  # Always rewarded slightly for taking action

    elif action_type == ActionType.ROLLBACK_DEPLOYMENT:
        service = action_payload.get("service")
        if service == ground_truth.get("root_cause_service"):
            reward += 0.12  # Major reward for fixing root cause
        else:
            reward += 0.02

    elif action_type == ActionType.SCALE_UP:
        reward += 0.02

    # Small penalty for inefficient escalation (escalating before investigating)
    elif action_type == "escalate" and step < 3:
        reward -= 0.03  # Penalise immediate escalation without investigation

    # Time pressure penalty — reward decays slightly as steps increase
    step_penalty = -0.01 * (step / max_steps)
    reward += step_penalty

    return _clamp(reward, 0.0, 0.15)
