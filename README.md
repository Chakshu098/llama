# Llama-IR: Autonomous SRE Command Center

**Llama-IR** is a high-fidelity, multi-agent incident response system designed for the Meta Hackathon. It leverages a **Supervisor-Specialist** architecture to autonomously triage, investigate, and remediate service outages in complex microservice environments.

## 🚀 Key Features

- **Autonomous Orchestration**: A dynamic Supervisor agent delegating tasks to Triage, Investigator, and Remediation specialists.
- **Glassmorphism Command Center**: A modern React + Tailwind dashboard providing real-time observability into agent reasoning and service topology.
- **OpenEnv Compliance**: Built on top of the OpenEnv specification with typed Pydantic models for actions and observations.
- **Explainable AI**: Real-time "Thought Stream" showing exactly how agents identify root causes and plan recovery steps.

## 🛠 Tech Stack

- **Reasoning Engine**: Qwen2.5-72B-Instruct via Hugging Face Cloud.
- **Backend**: FastAPI with standard OpenEnv `step`/`reset` endpoints.
- **Frontend**: Vite + React + TypeScript + Tailwind CSS + Framer Motion.
- **Infrastructure**: Dockerized for seamless deployment to Hugging Face Spaces.

## 🏃 Quick Start

### 1. Requirements
- Python 3.13+
- Node.js & npm (for dashboard development)
- [HF_TOKEN](https://huggingface.co/settings/tokens) with access to Qwen2.5-72B.

### 2. Installation
```bash
pip install -r requirements.txt
cd dashboard-v3 && npm install && npm run build && cd ..
```

### 3. Run the Command Center
```bash
python server/app.py
```
Open `http://localhost:7861/dashboard` to view the UI.

### 4. Start the Agents
In a separate terminal:
```bash
python inference.py
```

## 🧩 Project Structure & OpenEnv Spec

This environment implements the full **OpenEnv** specification, providing a standard `step()` / `reset()` / `state()` interface for AI agents.

### 🎮 Action Space (Discrete & Typed)
- **`acknowledge`**: Mark alerts as seen to prevent escalation noise.
- **`query_logs(service: str)`**: Retrieve recent stdout/stderr logs for a specific service.
- **`query_topology`**: Discover service dependencies and health status.
- **`restart_service(service: str)`**: Attempt service recovery via container restart.
- **`rollback_deployment(service: str)`**: Revert to the last known stable image tag.
- **`scale_up(service: str)`**: Increase replica count for capacity-related issues.
- **`classify_alert(alert_id: str, is_root_cause: bool)`**: Terminal action for Task 1.
- **`resolve_incident`**: Signifies the agent has completed remediation.
- **`write_postmortem(content: str)`**: Terminal action for Task 3.

### 👁️ Observation Space
- **`alerts`**: List of active system alerts with severity and service metadata.
- **`logs`**: Stream of log entries filtered by time and relevance.
- **`topology`**: A dynamic graph of service nodes and their health states (Healthy/Critical).
- **`current_thoughts`**: Multi-agent shared reasoning buffer.
- **`recovery_status`**: Real-time progress tracker for the incident lifecycle.

## 📊 Evaluation & Graders
Llama-IR is benchmarked against three core tasks of increasing complexity. Each is evaluated by a deterministic programmatic grader (0.0–1.0 score):

| Task ID | Name | Difficulty | Description |
| :--- | :--- | :--- | :--- |
| `alert-classification` | Alert Triage | **Easy** | Map 10+ alerts to a single root cause alert. |
| `root-cause-analysis` | Diagnosis | **Medium** | Correlate logs across 3 services to find a config error. |
| `postmortem-writing` | SEV-1 Report | **Hard** | Generate a professional timeline and action items. |

## 🚀 Deployment & Submission
This project is pre-configured for **Hugging Face Spaces**:
1. The `Dockerfile` exposes port `7861` and handles both the FastAPI backend and React frontend.
2. The `openenv.yaml` defines the metadata and task entrypoints for the automated grader.
3. The `inference.py` strictly follows the `[START]/[STEP]/[END]` STDOUT protocol.

### Local baseline run
```bash
python inference.py
```
Expected baseline score (Qwen 72B): **~0.85 - 0.92** (Average across tasks).
