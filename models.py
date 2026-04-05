from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from typing import Any, Dict, List, Optional


class ActionType(str, Enum):
    # --- Standard OpenEnv actions ---
    ACKNOWLEDGE = "acknowledge"
    QUERY_LOGS = "query_logs"
    QUERY_TOPOLOGY = "query_topology"
    RESTART_SERVICE = "restart_service"  # Advanced
    ROLLBACK_DEPLOYMENT = "rollback_deployment"  # Advanced
    SCALE_UP = "scale_up"  # Advanced

    # --- Terminal task actions ---
    CLASSIFY_ALERT = "classify_alert"
    RESOLVE_INCIDENT = "resolve_incident"
    WRITE_POSTMORTEM = "write_postmortem"


class AlertSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    ACTIVE = "active"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class AgentRole(str, Enum):
    SUPERVISOR = "Supervisor"
    TRIAGE = "Triage"
    INVESTIGATOR = "Investigator"
    REMEDIATION = "Remediation"
    REPORTER = "Reporter"


class AgentThought(BaseModel):
    role: AgentRole
    thought: str
    timestamp: float


class RecoveryTask(BaseModel):
    task_name: str
    completed: bool = False


class Alert(BaseModel):
    alert_id: str
    service: str
    severity: AlertSeverity
    message: str
    is_root_cause: bool = False


class LogEntry(BaseModel):
    timestamp: str
    service: str
    level: str
    message: str


class ServiceNode(BaseModel):
    name: str
    healthy: bool = True
    active_remediations: List[str] = []


class ServiceTopology(BaseModel):
    services: Dict[str, ServiceNode]


class Observation(BaseModel):
    alerts: List[Alert]
    logs: List[LogEntry]
    topology: ServiceTopology
    history: List[str]
    time_elapsed_seconds: int
    incident_status: IncidentStatus
    task_id: str
    step: int
    current_thoughts: List[AgentThought] = []
    actions_in_progress: List[str] = []
    recovery_status: List[RecoveryTask] = []


class Action(BaseModel):
    action_type: ActionType
    payload: Dict[str, Any]


class StepResult(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: Dict[str, Any]


class IncidentState(BaseModel):
    """Full environment state, primarily for API responses."""
    observation: Observation
    history: List[str]
    rewards: List[float]
    final_score: float = 0.0
    task_id: str
    step: int
    done: bool
    recovery_progress: float = 0.0
