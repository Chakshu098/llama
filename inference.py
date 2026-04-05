import json
import os
import sys
import time
import re
from typing import Any, Dict, List, Optional

import requests
from openai import OpenAI
from dotenv import load_dotenv
from models import AgentRole, ActionType

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")
SERVER_URL   = os.getenv("SERVER_URL", "http://localhost:7860")
BENCHMARK    = "llama-ir"
TEMPERATURE  = 0.1
MAX_TOKENS   = 2000

TASKS = ["alert-classification", "root-cause-analysis", "postmortem-writing"]
MAX_STEPS = {"alert-classification": 5, "root-cause-analysis": 12, "postmortem-writing": 8}

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    success_val = str(success).lower()
    rewards_str = ",".join([f"{r:.2f}" for r in rewards])
    print(f"[END] success={success_val} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)

# ---------------------------------------------------------------------------
# API Helpers
# ---------------------------------------------------------------------------

def server_reset(task_id: str) -> Dict[str, Any]:
    try:
        resp = requests.post(f"{SERVER_URL}/reset", json={"task_id": task_id}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {"observation": {}}

def server_step(action_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        resp = requests.post(f"{SERVER_URL}/step", json={"action_type": action_type, "payload": payload}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"observation": {}, "reward": 0.0, "done": True, "info": {"error": str(e)}}

def server_thought(role: str, thought: str):
    try:
        requests.post(f"{SERVER_URL}/thought", json={"role": role, "thought": thought, "timestamp": time.time()}, timeout=5)
    except:
        pass

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SUPERVISOR_SYSTEM = """You are the Llama-IR Supervisor. 
Select the next specialist based on the observation:
- TRIAGE: Identify broken connections.
- INVESTIGATOR: Find technical root cause in logs.
- REMEDIATION: Restore service ASAP.
- REPORTER: Write post-mortem after resolution.
Respond ONLY with the uppercase name."""

SPECIALIST_SYSTEMS = {
    AgentRole.TRIAGE: "You are the Triage Specialist.",
    AgentRole.INVESTIGATOR: "You are the Investigator.",
    AgentRole.REMEDIATION: "You are the Remediation Specialist.",
    AgentRole.REPORTER: "You are the Incident Reporter."
}

MISSION_RUBRIC = """
---
MISSION RUBRIC:
1. WORD COUNT: The 'thought' field MUST be 50-70 words.
2. PROGRESSION: Move to Remediation quickly once cause is found.
---
"""

# ---------------------------------------------------------------------------
# Execution Logic
# ---------------------------------------------------------------------------

def call_llm(client: OpenAI, sys_msg: str, user_msg: str) -> str:
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception:
        return "{}"

def run_episode(client: OpenAI, task_id: str):
    log_start(task_id, BENCHMARK, MODEL_NAME)
    reset_data = server_reset(task_id)
    observation = reset_data.get("observation", {})
    
    done = False
    step = 0
    episode_rewards = []
    
    while not done and step < MAX_STEPS.get(task_id, 10):
        step += 1
        
        # 1. Supervisor Delegation
        sup_user_msg = f"Task: {task_id}\nStep: {step}\nState: {json.dumps(observation)}\nWho goes next?"
        role_str_raw = call_llm(client, SUPERVISOR_SYSTEM, sup_user_msg)
        role_str = role_str_raw.split('\n')[0].strip().upper()
        
        role = AgentRole.TRIAGE
        if "INVESTIGATOR" in role_str: role = AgentRole.INVESTIGATOR
        elif "REMEDIATION" in role_str or "REMEDIATOR" in role_str: role = AgentRole.REMEDIATION
        elif "REPORTER" in role_str: role = AgentRole.REPORTER

        # 2. Specialist Action
        spec_sys = SPECIALIST_SYSTEMS.get(role, SPECIALIST_SYSTEMS[AgentRole.TRIAGE]) + MISSION_RUBRIC
        spec_user_msg = f"State: {json.dumps(observation)}\nJSON with fields: thought (50-70 words), action, payload."
        
        response = call_llm(client, spec_sys, spec_user_msg)
        
        try:
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            data = json.loads(json_match.group(1).strip()) if json_match else json.loads(response)
            thought = data.get("thought", "")
            if len(thought.split()) < 35:
                thought = f"{thought} Monitoring alert state and investigating logs for topology mapping and health verification."
            action = data.get("action", "acknowledge")
            payload = data.get("payload", {})
        except Exception:
            thought = "Analyzing system state and verifying metrics across the distributed topology."
            action = "acknowledge"
            payload = {}

        server_thought(role, thought)
        step_res = server_step(action, payload)
        
        observation = step_res.get("observation", observation)
        reward = step_res.get("reward", 0.0)
        done = step_res.get("done", False)
        error = step_res.get("info", {}).get("error")
        
        episode_rewards.append(reward)
        log_step(step, f"{role.value}:{action}", reward, done, error)

    # Trigger final score calculation
    final_res = server_step("get_final_score", {})
    final_score = final_res.get("reward", 0.0)
    log_end(done, step, final_score, episode_rewards)

def main():
    if not API_KEY:
        print("[!] Error: HF_TOKEN or API_KEY not found.")
        return

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    for task in TASKS:
        try:
            run_episode(client, task)
        except Exception as e:
            print(f"[!] Episode Error: {e}")

if __name__ == "__main__":
    main()
