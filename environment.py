"""
environment.py — Core OpenEnv environment implementation.

Implements the full OpenEnv interface:
  reset()  → Observation
  step()   → StepResult
  state()  → dict
  close()  → None
"""

from __future__ import annotations

import random
import time
from copy import deepcopy
from typing import Any, Dict, List, Optional

from models import (
    Action, ActionType, Alert, LogEntry, Observation,
    ServiceTopology, ServiceNode, StepResult, IncidentStatus,
    AgentThought, RecoveryTask, AgentRole
)
from graders import (
    AlertClassificationGrader,
    RootCauseAnalysisGrader,
    PostMortemGrader,
    compute_step_reward,
)
from scenarios import (
    ALERT_CLASSIFICATION_SCENARIOS,
    ROOT_CAUSE_SCENARIOS,
    POSTMORTEM_SCENARIOS,
)


TASK_SCENARIOS = {
    "alert-classification": ALERT_CLASSIFICATION_SCENARIOS,
    "root-cause-analysis":  ROOT_CAUSE_SCENARIOS,
    "postmortem-writing":   POSTMORTEM_SCENARIOS,
}

TASK_MAX_STEPS = {
    "alert-classification": 10,
    "root-cause-analysis":  15,
    "postmortem-writing":   20,
}

TASK_SUCCESS_THRESHOLD = {
    "alert-classification": 0.60,
    "root-cause-analysis":  0.60,
    "postmortem-writing":   0.50,
}


class IncidentResponseEnv:
    """
    OpenEnv-compliant Incident Response environment.

    Supports three tasks of increasing difficulty:
      - alert-classification  (easy)
      - root-cause-analysis   (medium)
      - postmortem-writing    (hard)
    """

    def __init__(self, task_id: str = "alert-classification", scenario_id: Optional[str] = None):
        if task_id not in TASK_SCENARIOS:
            raise ValueError(f"Unknown task_id '{task_id}'. Choose from: {list(TASK_SCENARIOS)}")

        self.task_id = task_id
        self.scenario_id = scenario_id
        self._scenario: Dict[str, Any] = {}
        self._observation: Optional[Observation] = None
        self._step_count: int = 0
        self._start_time: float = 0.0
        self._done: bool = False
        self._rewards: List[float] = []
        self._history: List[str] = []
        self._final_score: float = 0.0
        self._score_breakdown: Dict[str, Any] = {}
        
        # --- Advanced Dashboard Telemetry ---
        self._current_thoughts: List[AgentThought] = []
        self._actions_in_progress: List[str] = []
        self._recovery_status: List[RecoveryTask] = [
            RecoveryTask(task_name="Monitor Alerts", completed=True),
            RecoveryTask(task_name="Triage Incident", completed=False),
            RecoveryTask(task_name="Root Cause Analysis", completed=False),
            RecoveryTask(task_name="Remediation", completed=False),
            RecoveryTask(task_name="Final Verification", completed=False),
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(self) -> Observation:
        """Reset the environment and return the initial observation."""
        scenarios = TASK_SCENARIOS[self.task_id]

        if self.scenario_id:
            matches = [s for s in scenarios if s["id"] == self.scenario_id]
            if not matches:
                raise ValueError(f"Scenario '{self.scenario_id}' not found for task '{self.task_id}'")
            self._scenario = deepcopy(matches[0])
        else:
            self._scenario = deepcopy(random.choice(scenarios))

        self._step_count = 0
        self._done = False
        self._rewards = []
        self._history = []
        self._start_time = time.time()
        
        # Reset telemetry
        self._current_thoughts = []
        self._actions_in_progress = []
        self._recovery_status = [
            RecoveryTask(task_name="Monitor Alerts", completed=True),
            RecoveryTask(task_name="Triage Incident", completed=False),
            RecoveryTask(task_name="Root Cause Analysis", completed=False),
            RecoveryTask(task_name="Remediation", completed=False),
            RecoveryTask(task_name="Final Verification", completed=False),
        ]

        self._observation = self._build_observation(step=0)
        return self._observation

    def step(self, action: Action) -> StepResult:
        """Process one agent action and return (observation, reward, done, info)."""
        if self._done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")
        if self._observation is None:
            raise RuntimeError("Call reset() before step().")

        self._step_count += 1
        action_type = action.action_type
        payload = action.payload

        # Update Telemetry based on action
        if action_type == ActionType.ACKNOWLEDGE:
            self._recovery_status[1].completed = True
        elif action_type == ActionType.QUERY_LOGS:
            self._recovery_status[2].completed = True
        elif action_type in [ActionType.RESTART_SERVICE, ActionType.ROLLBACK_DEPLOYMENT, ActionType.SCALE_UP]:
            self._recovery_status[3].completed = True
            service = payload.get("service", "General")
            self._actions_in_progress = [f"{action_type.replace('_', ' ').title()} ({service})"]

        # --- Per-step dense reward ---
        step_reward = compute_step_reward(
            action_type=action_type,
            action_payload=payload,
            observation_before=self._observation.model_dump(),
            ground_truth=self._scenario.get("ground_truth", {}),
            step=self._step_count,
            max_steps=TASK_MAX_STEPS[self.task_id],
        )

        # --- Terminal actions that trigger final grading ---
        final_score = 0.0
        done = False
        info: Dict[str, Any] = {"step_reward": step_reward, "action_type": action_type}

        if action_type == ActionType.CLASSIFY_ALERT and self.task_id == "alert-classification":
            grader = AlertClassificationGrader(self._scenario)
            final_score, breakdown = grader.grade(payload)
            done = True
            info["final_score"] = final_score
            info["breakdown"] = breakdown

        elif action_type == ActionType.RESOLVE_INCIDENT and self.task_id == "root-cause-analysis":
            grader = RootCauseAnalysisGrader(self._scenario)
            final_score, breakdown = grader.grade(payload)
            done = True
            info["final_score"] = final_score
            info["breakdown"] = breakdown

        elif action_type == ActionType.WRITE_POSTMORTEM and self.task_id == "postmortem-writing":
            grader = PostMortemGrader(self._scenario)
            final_score, breakdown = grader.grade(payload)
            done = True
            info["final_score"] = final_score
            info["breakdown"] = breakdown

        elif action_type == ActionType.RESTART_SERVICE:
            service = payload.get("service")
            if service in self._scenario.get("topology", {}).get("services", {}):
                self._scenario["topology"]["services"][service]["healthy"] = True
                action_summary = f"Restarted service {service}"
                self._history.append(action_summary)
                step_reward += 0.05
            else:
                info["error"] = f"Service {service} not found"

        elif action_type == ActionType.ROLLBACK_DEPLOYMENT:
            service = payload.get("service")
            if service == self._scenario.get("ground_truth", {}).get("root_cause_service"):
                action_summary = f"Rolled back deployment for {service} (Root Cause Fixed)"
                self._history.append(action_summary)
                step_reward += 0.2
            else:
                action_summary = f"Rolled back deployment for {service}"
                self._history.append(action_summary)

        elif action_type == ActionType.SCALE_UP:
            service = payload.get("service")
            action_summary = f"Scaled up service {service}"
            self._history.append(action_summary)
            step_reward += 0.05

        # --- Max steps reached ---
        if self._step_count >= TASK_MAX_STEPS[self.task_id]:
            done = True

        # --- Combine rewards ---
        if done and final_score > 0:
            # Weight: 70% final graded score + 30% accumulated step rewards
            accumulated = sum(self._rewards) / max(len(self._rewards), 1)
            total_reward = round(0.70 * final_score + 0.30 * accumulated, 4)
            self._recovery_status[4].completed = True
        elif done:
            total_reward = round(step_reward, 4)
        else:
            total_reward = round(step_reward, 4)

        self._rewards.append(total_reward)
        self._done = done
        self._final_score = final_score
        self._score_breakdown = info.get("breakdown", {})

        # Build next observation
        elapsed = int(time.time() - self._start_time)
        status = IncidentStatus.RESOLVED if done and final_score >= TASK_SUCCESS_THRESHOLD[self.task_id] \
            else IncidentStatus.INVESTIGATING
        self._observation = self._build_observation(step=self._step_count, status=status)

        return StepResult(
            observation=self._observation,
            reward=total_reward,
            done=done,
            info=info,
        )

    def state(self) -> Dict[str, Any]:
        """Return current internal state (for debugging / inspection)."""
        return {
            "task_id": self.task_id,
            "scenario_id": self._scenario.get("id"),
            "step": self._step_count,
            "done": self._done,
            "rewards": self._rewards,
            "history": self._history,
            "final_score": self._final_score,
            "score_breakdown": self._score_breakdown,
            "elapsed_seconds": int(time.time() - self._start_time) if self._start_time else 0,
            "observation": self._observation.model_dump() if self._observation else {},
            "recovery_progress": sum(1 for t in self._recovery_status if t.completed) / len(self._recovery_status)
        }

    def record_thought(self, role: AgentRole, thought: str):
        """Record an agent's thought for the dashboard."""
        self._current_thoughts.append(AgentThought(
            role=role,
            thought=thought,
            timestamp=time.time()
        ))
        # Keep only the last 15 thoughts to avoid bloat
        self._current_thoughts = self._current_thoughts[-15:]

    def close(self) -> None:
        """Cleanup (no-op for this environment — nothing to close)."""
        pass

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_observation(
        self,
        step: int,
        status: IncidentStatus = IncidentStatus.ACTIVE,
    ) -> Observation:
        elapsed = int(time.time() - self._start_time) if self._start_time else 0

        # Build alerts (hide ground truth is_root_cause from agent view)
        alerts = []
        for a in self._scenario.get("alerts", []):
            alert_data = {k: v for k, v in a.items() if k != "is_root_cause"}
            alerts.append(Alert(**alert_data, is_root_cause=False))  # hidden

        # Build logs
        logs = [LogEntry(**l) for l in self._scenario.get("logs", [])]

        # Build topology
        topo_data = self._scenario.get("topology", {})
        services = {}
        for name, node in topo_data.get("services", {}).items():
            node_data = node.copy()
            # In Observation, we don't necessarily show if a node is the root cause
            services[name] = ServiceNode(name=name, **node_data)
        topology = ServiceTopology(services=services)

        return Observation(
            alerts=alerts,
            logs=logs,
            topology=topology,
            history=list(self._history),
            time_elapsed_seconds=elapsed,
            incident_status=status,
            task_id=self.task_id,
            step=step,
            current_thoughts=list(self._current_thoughts),
            actions_in_progress=list(self._actions_in_progress),
            recovery_status=list(self._recovery_status),
        )
