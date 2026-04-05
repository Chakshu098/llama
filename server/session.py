"""
server/session.py — Multi-session support for parallel agent episodes.

Allows multiple agents to run concurrent episodes against the same server,
each with their own isolated environment state.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Dict, Optional

from environment import IncidentResponseEnv


class SessionManager:
    """
    Thread-safe session registry.

    Each session maps a session_id → IncidentResponseEnv instance.
    Sessions expire after IDLE_TIMEOUT_S seconds of inactivity.
    """

    IDLE_TIMEOUT_S = 600  # 10 minutes

    def __init__(self):
        self._sessions: Dict[str, dict] = {}
        self._lock = threading.Lock()
        # Background reaper thread
        self._reaper = threading.Thread(target=self._reap_idle, daemon=True)
        self._reaper.start()

    def create(self, task_id: str, scenario_id: Optional[str] = None) -> str:
        """Create a new session. Returns session_id."""
        session_id = str(uuid.uuid4())
        env = IncidentResponseEnv(task_id=task_id, scenario_id=scenario_id)
        with self._lock:
            self._sessions[session_id] = {
                "env": env,
                "created_at": time.time(),
                "last_active": time.time(),
                "task_id": task_id,
            }
        return session_id

    def get(self, session_id: str) -> Optional[IncidentResponseEnv]:
        """Get env for session_id, updating last_active. Returns None if not found."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session["last_active"] = time.time()
                return session["env"]
        return None

    def close(self, session_id: str) -> bool:
        """Close and remove a session. Returns True if found."""
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                session["env"].close()
                return True
        return False

    def list_sessions(self) -> list:
        """Return summary of all active sessions."""
        with self._lock:
            now = time.time()
            return [
                {
                    "session_id": sid,
                    "task_id": s["task_id"],
                    "age_s": int(now - s["created_at"]),
                    "idle_s": int(now - s["last_active"]),
                }
                for sid, s in self._sessions.items()
            ]

    def _reap_idle(self):
        """Background thread: close sessions idle longer than IDLE_TIMEOUT_S."""
        while True:
            time.sleep(60)
            now = time.time()
            with self._lock:
                to_reap = [
                    sid for sid, s in self._sessions.items()
                    if now - s["last_active"] > self.IDLE_TIMEOUT_S
                ]
            for sid in to_reap:
                self.close(sid)


# Global singleton used by the FastAPI app
session_manager = SessionManager()
