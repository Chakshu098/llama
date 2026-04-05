"""
scenarios.py — Realistic incident scenarios for all three tasks.

Each scenario is a self-contained dict that the environment loads.
Ground truth (root_cause, expected classifications, postmortem fields)
is embedded here and used by the graders — never exposed to the agent.
"""

from __future__ import annotations
from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# TASK 1: Alert Classification (easy) — 4 scenarios, varying topologies
# ---------------------------------------------------------------------------

ALERT_CLASSIFICATION_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "sc-ac-001",
        "description": "Payment service timeout cascade — database is root cause",
        "alerts": [
            {
                "alert_id": "ALT-001", "service": "payment-service",
                "severity": "critical", "is_root_cause": False,
                "message": "Payment service P99 latency exceeded 5000ms (threshold: 500ms)",
                "timestamp": "2024-03-15T14:32:01Z",
                "tags": {"env": "prod", "region": "us-east-1"}
            },
            {
                "alert_id": "ALT-002", "service": "postgres-primary",
                "severity": "critical", "is_root_cause": True,
                "message": "PostgreSQL connection pool exhausted: 500/500 connections in use, queue depth 847",
                "timestamp": "2024-03-15T14:31:47Z",
                "tags": {"env": "prod", "region": "us-east-1", "db": "payments-db"}
            },
            {
                "alert_id": "ALT-003", "service": "checkout-api",
                "severity": "high", "is_root_cause": False,
                "message": "Checkout API error rate 34% (threshold: 1%)",
                "timestamp": "2024-03-15T14:32:15Z",
                "tags": {"env": "prod", "region": "us-east-1"}
            },
            {
                "alert_id": "ALT-004", "service": "fraud-detection",
                "severity": "medium", "is_root_cause": False,
                "message": "Fraud detection response time degraded: 2100ms avg (threshold: 300ms)",
                "timestamp": "2024-03-15T14:32:30Z",
                "tags": {"env": "prod"}
            },
            {
                "alert_id": "ALT-005", "service": "notification-service",
                "severity": "low", "is_root_cause": False,
                "message": "Email notification queue depth: 12,400 (threshold: 1000). Consumers backed up.",
                "timestamp": "2024-03-15T14:33:01Z",
                "tags": {"env": "prod"}
            }
        ],
        "logs": [
            {
                "timestamp": "2024-03-15T14:31:45Z", "service": "postgres-primary",
                "level": "ERROR",
                "message": "FATAL: remaining connection slots are reserved for non-replication superuser connections",
                "trace_id": None
            },
            {
                "timestamp": "2024-03-15T14:31:48Z", "service": "payment-service",
                "level": "ERROR",
                "message": "Failed to acquire DB connection after 5000ms timeout: HikariPool-1 - Connection is not available",
                "trace_id": "trace-8f3a2"
            },
            {
                "timestamp": "2024-03-15T14:31:52Z", "service": "checkout-api",
                "level": "ERROR",
                "message": "Upstream payment-service returned 503 after 5001ms. Retrying (attempt 1/3)",
                "trace_id": "trace-9c1b4"
            },
            {
                "timestamp": "2024-03-15T14:32:00Z", "service": "postgres-primary",
                "level": "ERROR",
                "message": "Autovacuum worker on table payments.transactions blocked for 180s. Long-running query detected.",
                "trace_id": None
            }
        ],
        "topology": {
            "services": {
                "checkout-api":      {"upstream": ["payment-service", "fraud-detection"], "downstream": [], "healthy": False},
                "payment-service":   {"upstream": ["postgres-primary"], "downstream": ["checkout-api", "notification-service"], "healthy": False},
                "fraud-detection":   {"upstream": ["postgres-primary"], "downstream": ["checkout-api"], "healthy": False},
                "postgres-primary":  {"upstream": [], "downstream": ["payment-service", "fraud-detection"], "healthy": False},
                "notification-service": {"upstream": ["payment-service"], "downstream": [], "healthy": False}
            }
        },
        "ground_truth": {
            "root_cause_alert_id": "ALT-002",
            "root_cause_service": "postgres-primary",
            "blast_radius": ["payment-service", "checkout-api", "fraud-detection", "notification-service"],
            "correct_severity_map": {
                "ALT-001": "critical", "ALT-002": "critical",
                "ALT-003": "high", "ALT-004": "medium", "ALT-005": "low"
            }
        }
    },
    {
        "id": "sc-ac-002",
        "description": "Redis cache failure causing auth service storm",
        "alerts": [
            {
                "alert_id": "ALT-101", "service": "redis-session-cache",
                "severity": "critical", "is_root_cause": True,
                "message": "Redis node redis-prod-03 unreachable. Cluster failover initiated.",
                "timestamp": "2024-03-16T09:14:02Z",
                "tags": {"env": "prod", "cluster": "session-cache"}
            },
            {
                "alert_id": "ALT-102", "service": "auth-service",
                "severity": "critical", "is_root_cause": False,
                "message": "Session validation failure rate: 89%. Falling back to DB reads.",
                "timestamp": "2024-03-16T09:14:18Z",
                "tags": {"env": "prod"}
            },
            {
                "alert_id": "ALT-103", "service": "api-gateway",
                "severity": "high", "is_root_cause": False,
                "message": "401 Unauthorized responses: 23,000/min (normal: 50/min)",
                "timestamp": "2024-03-16T09:14:35Z",
                "tags": {"env": "prod"}
            },
            {
                "alert_id": "ALT-104", "service": "postgres-primary",
                "severity": "high", "is_root_cause": False,
                "message": "Unexpected spike in SELECT queries on sessions table: 45,000 QPS (normal: 200 QPS)",
                "timestamp": "2024-03-16T09:14:40Z",
                "tags": {"env": "prod"}
            },
            {
                "alert_id": "ALT-105", "service": "user-dashboard",
                "severity": "medium", "is_root_cause": False,
                "message": "Login success rate dropped to 11%",
                "timestamp": "2024-03-16T09:15:01Z",
                "tags": {"env": "prod"}
            },
            {
                "alert_id": "ALT-106", "service": "cdn-edge",
                "severity": "low", "is_root_cause": False,
                "message": "Cache bypass rate increased to 67% (threshold: 20%). Increased origin traffic.",
                "timestamp": "2024-03-16T09:15:30Z",
                "tags": {"env": "prod"}
            }
        ],
        "logs": [
            {
                "timestamp": "2024-03-16T09:13:58Z", "service": "redis-session-cache",
                "level": "ERROR",
                "message": "Connection refused to redis-prod-03:6379. OOM killer terminated redis process.",
                "trace_id": None
            },
            {
                "timestamp": "2024-03-16T09:14:10Z", "service": "auth-service",
                "level": "WARN",
                "message": "Redis GET timeout after 100ms for key session:usr_4829a. Falling back to Postgres.",
                "trace_id": "trace-d92f1"
            },
            {
                "timestamp": "2024-03-16T09:14:22Z", "service": "auth-service",
                "level": "ERROR",
                "message": "DB fallback latency 3200ms for session lookup. DB pool 180/200 connections used.",
                "trace_id": "trace-d93a2"
            }
        ],
        "topology": {
            "services": {
                "api-gateway":           {"upstream": ["auth-service"], "downstream": [], "healthy": False},
                "auth-service":          {"upstream": ["redis-session-cache", "postgres-primary"], "downstream": ["api-gateway", "user-dashboard"], "healthy": False},
                "redis-session-cache":   {"upstream": [], "downstream": ["auth-service"], "healthy": False},
                "postgres-primary":      {"upstream": [], "downstream": ["auth-service"], "healthy": True},
                "user-dashboard":        {"upstream": ["auth-service"], "downstream": [], "healthy": False},
                "cdn-edge":              {"upstream": ["user-dashboard"], "downstream": [], "healthy": False}
            }
        },
        "ground_truth": {
            "root_cause_alert_id": "ALT-101",
            "root_cause_service": "redis-session-cache",
            "blast_radius": ["auth-service", "api-gateway", "user-dashboard", "cdn-edge", "postgres-primary"],
            "correct_severity_map": {
                "ALT-101": "critical", "ALT-102": "critical",
                "ALT-103": "high", "ALT-104": "high",
                "ALT-105": "medium", "ALT-106": "low"
            }
        }
    }
]


# ---------------------------------------------------------------------------
# TASK 2: Root Cause Analysis (medium) — multi-hop log correlation
# ---------------------------------------------------------------------------

ROOT_CAUSE_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "sc-rca-001",
        "description": "Kubernetes node OOM → pod eviction → traffic spike → cache stampede",
        "alerts": [
            {
                "alert_id": "ALT-201", "service": "product-catalog",
                "severity": "critical", "is_root_cause": False,
                "message": "Product catalog service returning 503 for 78% of requests",
                "timestamp": "2024-03-17T16:05:10Z",
                "tags": {"env": "prod", "k8s_namespace": "default"}
            },
            {
                "alert_id": "ALT-202", "service": "recommendation-engine",
                "severity": "high", "is_root_cause": False,
                "message": "Recommendation engine pod CrashLoopBackOff on nodes: k8s-node-07, k8s-node-08",
                "timestamp": "2024-03-17T16:04:55Z",
                "tags": {"env": "prod", "k8s_node": "k8s-node-07"}
            },
            {
                "alert_id": "ALT-203", "service": "k8s-node-07",
                "severity": "critical", "is_root_cause": True,
                "message": "Node k8s-node-07 MemoryPressure=True. OOMKiller active. 3 pods evicted.",
                "timestamp": "2024-03-17T16:04:41Z",
                "tags": {"env": "prod", "node": "k8s-node-07", "available_memory_mb": "142"}
            },
            {
                "alert_id": "ALT-204", "service": "search-service",
                "severity": "high", "is_root_cause": False,
                "message": "Search service latency P99 degraded to 8200ms (SLO: 800ms)",
                "timestamp": "2024-03-17T16:05:30Z",
                "tags": {"env": "prod"}
            },
            {
                "alert_id": "ALT-205", "service": "memcached-cluster",
                "severity": "medium", "is_root_cause": False,
                "message": "Memcached cache hit rate dropped from 94% to 31%. Eviction rate spiking.",
                "timestamp": "2024-03-17T16:05:45Z",
                "tags": {"env": "prod", "cluster": "product-cache"}
            }
        ],
        "logs": [
            {
                "timestamp": "2024-03-17T16:04:38Z", "service": "k8s-node-07",
                "level": "ERROR",
                "message": "Out of memory: Kill process 28471 (java) score 892 or sacrifice child. oom_kill_process: Killed process 28471 (recommendation-engine)",
                "trace_id": None
            },
            {
                "timestamp": "2024-03-17T16:04:41Z", "service": "k8s-node-07",
                "level": "WARN",
                "message": "Evicting pod recommendation-engine-6d9f7b-xkp2q from node k8s-node-07 due to MemoryPressure",
                "trace_id": None
            },
            {
                "timestamp": "2024-03-17T16:04:55Z", "service": "product-catalog",
                "level": "WARN",
                "message": "Evicted recommendation-engine pod was pre-warming product-catalog cache. Cache cold for services: product-detail, search-service",
                "trace_id": None
            },
            {
                "timestamp": "2024-03-17T16:05:02Z", "service": "product-catalog",
                "level": "ERROR",
                "message": "Cache miss storm: 4,200 req/s to Postgres products table (normal: 180 req/s). Connection pool saturating.",
                "trace_id": "trace-f11c2"
            },
            {
                "timestamp": "2024-03-17T16:05:10Z", "service": "search-service",
                "level": "ERROR",
                "message": "product-catalog upstream returning 503. Retries exhausted. Circuit breaker OPEN.",
                "trace_id": "trace-g22d3"
            },
            {
                "timestamp": "2024-03-17T16:04:30Z", "service": "k8s-node-07",
                "level": "INFO",
                "message": "ML training job ml-batch-retraining-20240317 scheduled on k8s-node-07. Requesting 28Gi memory (node capacity: 32Gi)",
                "trace_id": None
            }
        ],
        "topology": {
            "services": {
                "k8s-node-07":          {"upstream": [], "downstream": ["recommendation-engine", "product-catalog"], "healthy": False},
                "recommendation-engine": {"upstream": ["k8s-node-07", "memcached-cluster"], "downstream": ["product-catalog"], "healthy": False},
                "product-catalog":      {"upstream": ["recommendation-engine", "memcached-cluster", "postgres-primary"], "downstream": ["search-service", "user-dashboard"], "healthy": False},
                "search-service":       {"upstream": ["product-catalog"], "downstream": [], "healthy": False},
                "memcached-cluster":    {"upstream": [], "downstream": ["product-catalog", "recommendation-engine"], "healthy": False},
                "postgres-primary":     {"upstream": [], "downstream": ["product-catalog"], "healthy": True}
            }
        },
        "ground_truth": {
            "root_cause_alert_id": "ALT-203",
            "root_cause_service": "k8s-node-07",
            "root_cause_description": "ML training job scheduled on k8s-node-07 consumed 28Gi of 32Gi node memory, triggering OOMKiller which evicted the recommendation-engine pod. The evicted pod was responsible for cache warming, causing a cache stampede in product-catalog which cascaded to search-service.",
            "causal_chain": [
                "ML training job requests 28Gi on 32Gi node",
                "OOMKiller evicts recommendation-engine pod",
                "recommendation-engine was warming product-catalog cache",
                "Cache hit rate drops from 94% → 31% (stampede)",
                "product-catalog floods Postgres with 4,200 req/s",
                "product-catalog returns 503",
                "search-service circuit breaker opens"
            ],
            "contributing_factors": [
                "ML training job lacked memory limits/quotas",
                "Cache warming was single-point-of-failure (only recommendation-engine pod)",
                "No cache stampede protection (e.g. mutex/lock)"
            ]
        }
    },
    {
        "id": "sc-rca-002",
        "description": "Misconfigured deploy causes certificate expiry → TLS handshake failures across microservices",
        "alerts": [
            {
                "alert_id": "ALT-301", "service": "api-gateway",
                "severity": "critical", "is_root_cause": False,
                "message": "TLS handshake failure rate: 97%. All downstream services unreachable.",
                "timestamp": "2024-03-18T11:20:05Z",
                "tags": {"env": "prod"}
            },
            {
                "alert_id": "ALT-302", "service": "cert-manager",
                "severity": "critical", "is_root_cause": True,
                "message": "Certificate renewal job cert-manager/wildcard-prod failed. Certificate expires in 00:03:14.",
                "timestamp": "2024-03-18T11:17:02Z",
                "tags": {"env": "prod", "cert": "wildcard-prod.example.com"}
            },
            {
                "alert_id": "ALT-303", "service": "order-service",
                "severity": "high", "is_root_cause": False,
                "message": "Order service cannot reach payment-service. SSL: CERTIFICATE_VERIFY_FAILED",
                "timestamp": "2024-03-18T11:20:12Z",
                "tags": {"env": "prod"}
            },
            {
                "alert_id": "ALT-304", "service": "payment-service",
                "severity": "high", "is_root_cause": False,
                "message": "Payment service cannot reach stripe-webhook-handler. TLS error.",
                "timestamp": "2024-03-18T11:20:18Z",
                "tags": {"env": "prod"}
            },
            {
                "alert_id": "ALT-305", "service": "monitoring-stack",
                "severity": "medium", "is_root_cause": False,
                "message": "Prometheus scrape failure for 43/67 targets. TLS certificate error.",
                "timestamp": "2024-03-18T11:20:30Z",
                "tags": {"env": "prod"}
            }
        ],
        "logs": [
            {
                "timestamp": "2024-03-18T11:16:45Z", "service": "cert-manager",
                "level": "ERROR",
                "message": "ACME challenge failed for wildcard-prod.example.com: DNS-01 challenge: provider 'route53' AccessDenied: IAM role cert-manager-prod missing route53:ChangeResourceRecordSets",
                "trace_id": None
            },
            {
                "timestamp": "2024-03-18T11:17:02Z", "service": "cert-manager",
                "level": "ERROR",
                "message": "Certificate wildcard-prod.example.com renewal failed after 3 attempts. Certificate will expire at 2024-03-18T11:23:00Z",
                "trace_id": None
            },
            {
                "timestamp": "2024-03-18T11:18:30Z", "service": "cert-manager",
                "level": "INFO",
                "message": "Last successful renewal: 2024-03-16T11:15:00Z. Note: IAM role cert-manager-prod was last modified 2024-03-16T10:52:00Z by deploy job deploy/infra-rbac-cleanup-v2.1.0",
                "trace_id": None
            },
            {
                "timestamp": "2024-03-18T11:20:02Z", "service": "api-gateway",
                "level": "ERROR",
                "message": "TLS error: x509: certificate has expired or is not yet valid: current time 2024-03-18T11:20:02Z is after 2024-03-18T11:20:00Z",
                "trace_id": None
            }
        ],
        "topology": {
            "services": {
                "cert-manager":           {"upstream": ["route53-dns"], "downstream": ["api-gateway", "order-service", "payment-service", "monitoring-stack"], "healthy": False},
                "api-gateway":            {"upstream": ["cert-manager"], "downstream": ["order-service", "payment-service"], "healthy": False},
                "order-service":          {"upstream": ["api-gateway", "payment-service"], "downstream": [], "healthy": False},
                "payment-service":        {"upstream": ["api-gateway", "cert-manager"], "downstream": ["stripe-webhook-handler"], "healthy": False},
                "monitoring-stack":       {"upstream": ["cert-manager"], "downstream": [], "healthy": False},
                "route53-dns":            {"upstream": [], "downstream": ["cert-manager"], "healthy": True}
            }
        },
        "ground_truth": {
            "root_cause_alert_id": "ALT-302",
            "root_cause_service": "cert-manager",
            "root_cause_description": "A deploy job (infra-rbac-cleanup-v2.1.0) removed the route53:ChangeResourceRecordSets permission from the cert-manager IAM role. When the certificate renewal job ran, it could not complete the DNS-01 ACME challenge and the wildcard certificate expired, causing TLS failures across all services.",
            "causal_chain": [
                "deploy/infra-rbac-cleanup-v2.1.0 removes route53 permission from cert-manager IAM role",
                "cert-manager cannot complete DNS-01 ACME challenge",
                "Certificate renewal fails after 3 attempts",
                "Wildcard certificate expires",
                "All services using the certificate get TLS handshake failures"
            ],
            "contributing_factors": [
                "No alerting on certificate renewal failures 48h before expiry",
                "IAM permission change not caught in RBAC change review",
                "Wildcard certificate is single point of TLS failure for all services"
            ]
        }
    }
]


# ---------------------------------------------------------------------------
# TASK 3: Post-Mortem Writing (hard) — full resolved incident timeline
# ---------------------------------------------------------------------------

POSTMORTEM_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "sc-pm-001",
        "description": "Complete incident: Database failover during peak traffic caused 47-minute checkout outage",
        "incident_summary": {
            "title": "Checkout Outage Due to Unplanned PostgreSQL Primary Failover — 2024-03-15",
            "duration_minutes": 47,
            "start_time": "2024-03-15T14:31:47Z",
            "end_time": "2024-03-15T15:18:52Z",
            "affected_services": ["postgres-primary", "payment-service", "checkout-api", "fraud-detection"],
            "user_impact": "~340,000 checkout attempts failed. Estimated $2.1M revenue impact. 18% of affected users did not return.",
            "severity": "SEV-1"
        },
        "timeline": [
            {"time": "14:22:00Z", "event": "Routine schema migration started on postgres-primary (payments.transactions table, adding index)"},
            {"time": "14:31:47Z", "event": "Autovacuum worker blocked by migration lock. Connection pool begins filling."},
            {"time": "14:31:55Z", "event": "PagerDuty alert fired: postgres-primary connection pool >90%"},
            {"time": "14:32:01Z", "event": "payment-service begins timing out. checkout-api error rate rises to 34%"},
            {"time": "14:32:10Z", "event": "On-call engineer (Alice) acknowledges alert"},
            {"time": "14:35:00Z", "event": "Alice attempts to kill blocking migration query — psql connection also times out"},
            {"time": "14:38:00Z", "event": "Decision made to initiate manual failover to postgres-replica-01"},
            {"time": "14:40:00Z", "event": "Failover initiated. Replication lag at time of failover: 8.2 seconds"},
            {"time": "14:40:30Z", "event": "postgres-replica-01 promoted to primary. Payment service reconnects."},
            {"time": "14:41:00Z", "event": "Discovery: 8.2s replication lag means ~12,000 transactions may be in inconsistent state"},
            {"time": "14:42:00Z", "event": "Incident escalated to database-team lead (Bob) and engineering manager"},
            {"time": "14:55:00Z", "event": "Bob runs reconciliation script. Confirms 847 transactions need manual review."},
            {"time": "15:10:00Z", "event": "payment-service fully recovered. checkout-api error rate back to baseline."},
            {"time": "15:18:52Z", "event": "Incident declared resolved. Monitoring period begins."}
        ],
        "alerts": [
            {
                "alert_id": "ALT-001", "service": "postgres-primary", "severity": "critical",
                "message": "PostgreSQL connection pool exhausted: 500/500 connections in use",
                "timestamp": "2024-03-15T14:31:55Z",
                "tags": {"env": "prod"}, "is_root_cause": True, "acknowledged": True
            },
            {
                "alert_id": "ALT-002", "service": "payment-service", "severity": "critical",
                "message": "Payment service P99 latency exceeded 5000ms",
                "timestamp": "2024-03-15T14:32:01Z",
                "tags": {"env": "prod"}, "is_root_cause": False, "acknowledged": True
            }
        ],
        "logs": [],
        "topology": {
            "services": {
                "postgres-primary": {"upstream": [], "downstream": ["payment-service", "fraud-detection"], "healthy": False},
                "payment-service":  {"upstream": ["postgres-primary"], "downstream": ["checkout-api"], "healthy": False},
                "checkout-api":     {"upstream": ["payment-service", "fraud-detection"], "downstream": [], "healthy": False},
                "fraud-detection":  {"upstream": ["postgres-primary"], "downstream": ["checkout-api"], "healthy": False}
            }
        },
        "ground_truth": {
            "required_sections": ["impact_summary", "timeline", "root_cause", "contributing_factors", "action_items", "lessons_learned"],
            "expected_root_cause_keywords": ["migration", "lock", "autovacuum", "connection pool", "schema"],
            "expected_contributing_factors": [
                "schema migration run during peak hours",
                "no migration lock timeout configured",
                "replication lag not checked before failover",
                "no automated connection draining"
            ],
            "required_action_item_themes": ["migration policy", "connection limits", "replication lag check", "runbook"],
            "minimum_timeline_events": 8,
            "minimum_action_items": 3
        }
    },
    {
        "id": "sc-pm-002",
        "description": "K8s node OOM → cache stampede → 22-minute product catalog degradation",
        "incident_summary": {
            "title": "Product Catalog Degradation Due to K8s Node OOM and Cache Stampede — 2024-03-17",
            "duration_minutes": 22,
            "start_time": "2024-03-17T16:04:38Z",
            "end_time": "2024-03-17T16:26:41Z",
            "affected_services": ["k8s-node-07", "recommendation-engine", "product-catalog", "search-service"],
            "user_impact": "~89,000 product page loads returned errors or partial content. Search unavailable for 18 minutes.",
            "severity": "SEV-2"
        },
        "timeline": [
            {"time": "16:04:30Z", "event": "ML training job scheduled on k8s-node-07 requesting 28Gi of 32Gi node memory"},
            {"time": "16:04:38Z", "event": "OOMKiller activates on k8s-node-07, kills recommendation-engine process"},
            {"time": "16:04:41Z", "event": "Kubernetes evicts recommendation-engine pod from k8s-node-07"},
            {"time": "16:04:55Z", "event": "Alert fires: recommendation-engine CrashLoopBackOff"},
            {"time": "16:05:02Z", "event": "Cache miss storm begins on product-catalog: 4,200 req/s to Postgres"},
            {"time": "16:05:10Z", "event": "search-service circuit breaker opens. Search returns 503."},
            {"time": "16:06:00Z", "event": "On-call engineer (Carol) acknowledges alerts"},
            {"time": "16:08:00Z", "event": "Carol identifies ML training job as suspect via kubectl describe node"},
            {"time": "16:09:00Z", "event": "ML training job terminated. k8s-node-07 memory pressure relieved."},
            {"time": "16:11:00Z", "event": "recommendation-engine pod rescheduled on k8s-node-12. Cache warming begins."},
            {"time": "16:18:00Z", "event": "Cache hit rate recovering: 31% → 78%"},
            {"time": "16:24:00Z", "event": "search-service circuit breaker closes. Error rate back to baseline."},
            {"time": "16:26:41Z", "event": "Incident resolved. Cache hit rate restored to 94%."}
        ],
        "alerts": [
            {
                "alert_id": "ALT-203", "service": "k8s-node-07", "severity": "critical",
                "message": "Node k8s-node-07 MemoryPressure=True. OOMKiller active.",
                "timestamp": "2024-03-17T16:04:41Z",
                "tags": {"env": "prod"}, "is_root_cause": True, "acknowledged": True
            }
        ],
        "logs": [],
        "topology": {
            "services": {
                "k8s-node-07":           {"upstream": [], "downstream": ["recommendation-engine"], "healthy": False},
                "recommendation-engine": {"upstream": ["k8s-node-07"], "downstream": ["product-catalog"], "healthy": False},
                "product-catalog":       {"upstream": ["recommendation-engine", "memcached-cluster"], "downstream": ["search-service"], "healthy": False},
                "search-service":        {"upstream": ["product-catalog"], "downstream": [], "healthy": False}
            }
        },
        "ground_truth": {
            "required_sections": ["impact_summary", "timeline", "root_cause", "contributing_factors", "action_items", "lessons_learned"],
            "expected_root_cause_keywords": ["ml training", "memory", "oom", "cache", "stampede", "recommendation-engine"],
            "expected_contributing_factors": [
                "ml training job had no memory limits",
                "cache warming single point of failure",
                "no cache stampede protection"
            ],
            "required_action_item_themes": ["resource quotas", "cache warming redundancy", "stampede protection", "ml job scheduling"],
            "minimum_timeline_events": 7,
            "minimum_action_items": 3
        }
    }
]


# ---------------------------------------------------------------------------
# Additional scenario: Task 1 (easy) — CDN edge misconfiguration
# ---------------------------------------------------------------------------

ALERT_CLASSIFICATION_SCENARIOS.append({
    "id": "sc-ac-003",
    "description": "CDN misconfiguration causes origin flood and latency spike",
    "alerts": [
        {
            "alert_id": "ALT-501", "service": "cdn-edge",
            "severity": "critical", "is_root_cause": True,
            "message": "CDN cache-control header misconfigured: TTL set to 0 across all routes. Cache bypass rate 100%.",
            "timestamp": "2024-04-01T10:02:11Z",
            "tags": {"env": "prod", "deploy": "cdn-config-v3.4.1"}
        },
        {
            "alert_id": "ALT-502", "service": "origin-api",
            "severity": "critical", "is_root_cause": False,
            "message": "Origin API receiving 18,000 req/s (normal: 800 req/s). CPU at 97%.",
            "timestamp": "2024-04-01T10:02:25Z",
            "tags": {"env": "prod"}
        },
        {
            "alert_id": "ALT-503", "service": "origin-api",
            "severity": "high", "is_root_cause": False,
            "message": "Origin API P99 latency: 9800ms (SLO: 200ms).",
            "timestamp": "2024-04-01T10:02:40Z",
            "tags": {"env": "prod"}
        },
        {
            "alert_id": "ALT-504", "service": "postgres-read-replica",
            "severity": "high", "is_root_cause": False,
            "message": "Read replica CPU 94%. Query queue depth 2,100.",
            "timestamp": "2024-04-01T10:03:00Z",
            "tags": {"env": "prod"}
        },
        {
            "alert_id": "ALT-505", "service": "user-service",
            "severity": "medium", "is_root_cause": False,
            "message": "User profile API timeout rate 41%.",
            "timestamp": "2024-04-01T10:03:20Z",
            "tags": {"env": "prod"}
        }
    ],
    "logs": [
        {
            "timestamp": "2024-04-01T10:02:08Z", "service": "cdn-edge",
            "level": "INFO",
            "message": "Config deploy cdn-config-v3.4.1 applied. cache-control: no-cache, no-store set globally.",
            "trace_id": None
        },
        {
            "timestamp": "2024-04-01T10:02:14Z", "service": "origin-api",
            "level": "WARN",
            "message": "Request rate spike detected: 4,200 req/s in last 10s. Autoscaler triggered.",
            "trace_id": None
        },
        {
            "timestamp": "2024-04-01T10:02:30Z", "service": "origin-api",
            "level": "ERROR",
            "message": "Thread pool exhausted. Requests queuing. Active threads: 512/512.",
            "trace_id": "trace-a1b2c"
        }
    ],
    "topology": {
        "services": {
            "cdn-edge":              {"upstream": [], "downstream": ["origin-api"], "healthy": False},
            "origin-api":            {"upstream": ["cdn-edge", "postgres-read-replica"], "downstream": ["user-service"], "healthy": False},
            "postgres-read-replica": {"upstream": [], "downstream": ["origin-api"], "healthy": False},
            "user-service":          {"upstream": ["origin-api"], "downstream": [], "healthy": False}
        }
    },
    "ground_truth": {
        "root_cause_alert_id": "ALT-501",
        "root_cause_service": "cdn-edge",
        "blast_radius": ["origin-api", "postgres-read-replica", "user-service"],
        "correct_severity_map": {
            "ALT-501": "critical", "ALT-502": "critical",
            "ALT-503": "high", "ALT-504": "high", "ALT-505": "medium"
        }
    }
})


# ---------------------------------------------------------------------------
# Additional scenario: Task 2 (medium) — Deployment config error → memory leak
# ---------------------------------------------------------------------------

ROOT_CAUSE_SCENARIOS.append({
    "id": "sc-rca-003",
    "description": "Bad deploy introduces memory leak in worker pool → gradual OOM over 90 minutes",
    "alerts": [
        {
            "alert_id": "ALT-401", "service": "worker-pool",
            "severity": "critical", "is_root_cause": False,
            "message": "Worker pool pods OOMKilled: 12/16 pods restarted in last 30 minutes.",
            "timestamp": "2024-04-02T03:45:00Z",
            "tags": {"env": "prod", "k8s_namespace": "workers"}
        },
        {
            "alert_id": "ALT-402", "service": "job-queue",
            "severity": "high", "is_root_cause": False,
            "message": "Job queue depth: 84,000 (normal: 200). Processing rate near zero.",
            "timestamp": "2024-04-02T03:45:15Z",
            "tags": {"env": "prod"}
        },
        {
            "alert_id": "ALT-403", "service": "deploy-pipeline",
            "severity": "critical", "is_root_cause": True,
            "message": "Deploy worker-pool-v2.8.3 completed at 02:14:00Z. Memory limit not set in new Deployment spec.",
            "timestamp": "2024-04-02T03:46:00Z",
            "tags": {"env": "prod", "deploy_id": "deploy-8821", "version": "v2.8.3"}
        },
        {
            "alert_id": "ALT-404", "service": "data-pipeline",
            "severity": "high", "is_root_cause": False,
            "message": "Batch data pipeline SLA breach: jobs older than 4h not processed (SLO: 30min).",
            "timestamp": "2024-04-02T03:47:00Z",
            "tags": {"env": "prod"}
        }
    ],
    "logs": [
        {
            "timestamp": "2024-04-02T02:14:05Z", "service": "deploy-pipeline",
            "level": "INFO",
            "message": "Deployment worker-pool-v2.8.3 applied. Diff: resources.limits.memory removed (was: 2Gi). PR #4421 merged by engineer-bot.",
            "trace_id": None
        },
        {
            "timestamp": "2024-04-02T02:45:00Z", "service": "worker-pool",
            "level": "WARN",
            "message": "Pod worker-pool-6d8f9-xkp1 RSS memory: 1.8Gi and growing. No limit set.",
            "trace_id": None
        },
        {
            "timestamp": "2024-04-02T03:15:00Z", "service": "worker-pool",
            "level": "ERROR",
            "message": "Pod worker-pool-6d8f9-xkp1 OOMKilled. RSS was 3.9Gi at time of kill.",
            "trace_id": None
        },
        {
            "timestamp": "2024-04-02T03:30:00Z", "service": "worker-pool",
            "level": "ERROR",
            "message": "8/16 pods OOMKilled. Job processing throughput: 12 jobs/min (normal: 1,400 jobs/min).",
            "trace_id": None
        },
        {
            "timestamp": "2024-04-02T03:45:00Z", "service": "job-queue",
            "level": "ERROR",
            "message": "Queue depth critical: 84,211 pending jobs. Oldest job enqueued 91 minutes ago.",
            "trace_id": None
        }
    ],
    "topology": {
        "services": {
            "deploy-pipeline": {"upstream": [], "downstream": ["worker-pool"], "healthy": False},
            "worker-pool":     {"upstream": ["deploy-pipeline", "job-queue"], "downstream": ["data-pipeline"], "healthy": False},
            "job-queue":       {"upstream": [], "downstream": ["worker-pool"], "healthy": False},
            "data-pipeline":   {"upstream": ["worker-pool"], "downstream": [], "healthy": False}
        }
    },
    "ground_truth": {
        "root_cause_alert_id": "ALT-403",
        "root_cause_service": "deploy-pipeline",
        "root_cause_description": "Deploy worker-pool-v2.8.3 (PR #4421) removed the memory limit from the worker Deployment spec. Without a limit, worker pods consumed unbounded memory over ~90 minutes until OOMKilled by the kernel, draining the worker pool and stalling the job queue.",
        "causal_chain": [
            "PR #4421 removes resources.limits.memory from worker-pool Deployment spec",
            "Deploy worker-pool-v2.8.3 applies the change at 02:14Z",
            "Worker pods begin leaking memory with no ceiling — RSS grows unchecked",
            "After ~60-90 minutes, pods exceed node available memory and are OOMKilled",
            "12/16 worker pods OOMKilled; processing throughput collapses",
            "Job queue depth grows to 84,000; data pipeline SLA breached"
        ],
        "contributing_factors": [
            "No CI/CD check enforcing memory limits on Deployment specs",
            "No alerting on pod memory growth rate (only on OOMKill events)",
            "Memory limit was removed by automated PR merge without human review"
        ]
    }
})


# ---------------------------------------------------------------------------
# Additional scenario: Task 3 (hard) — DNS misconfiguration outage
# ---------------------------------------------------------------------------

POSTMORTEM_SCENARIOS.append({
    "id": "sc-pm-003",
    "description": "DNS TTL misconfiguration caused 35-minute global service outage after nameserver change",
    "incident_summary": {
        "title": "Global Service Outage Due to DNS TTL Misconfiguration During Nameserver Migration — 2024-04-03",
        "duration_minutes": 35,
        "start_time": "2024-04-03T08:45:00Z",
        "end_time": "2024-04-03T09:20:00Z",
        "affected_services": ["all public-facing services", "api.example.com", "app.example.com"],
        "user_impact": "100% of external traffic failed for 35 minutes. ~520,000 users affected. All API calls returned NXDOMAIN.",
        "severity": "SEV-1"
    },
    "timeline": [
        {"time": "07:30:00Z", "event": "Planned nameserver migration from NS1 to Route53 begins. TTL lowered to 300s on old nameserver."},
        {"time": "08:00:00Z", "event": "New Route53 nameserver records created but TTL mistakenly set to 86400s (24h) instead of 300s."},
        {"time": "08:30:00Z", "event": "Old NS1 nameserver decommissioned as planned."},
        {"time": "08:45:00Z", "event": "Resolvers globally begin expiring cached NS records. Traffic fails — Route53 zone not yet propagated globally."},
        {"time": "08:47:00Z", "event": "PagerDuty fires: 100% of health checks failing globally. On-call engineer (Dave) paged."},
        {"time": "08:52:00Z", "event": "Dave identifies DNS resolution failing for api.example.com. Suspects nameserver issue."},
        {"time": "09:00:00Z", "event": "Root cause confirmed: TTL on Route53 NS records is 86400s, delaying propagation. Old NS is gone."},
        {"time": "09:05:00Z", "event": "Emergency: cannot reduce TTL on Route53 records — TTL must be served and waited out. Rollback impossible."},
        {"time": "09:10:00Z", "event": "Mitigation: configure temporary emergency IPs directly in SOA; contact major resolver operators (Google, Cloudflare) to flush cache manually."},
        {"time": "09:15:00Z", "event": "Google and Cloudflare resolvers flushed. ~60% of traffic recovers."},
        {"time": "09:18:00Z", "event": "Additional ISP resolvers flushed. Traffic recovery reaches 85%."},
        {"time": "09:20:00Z", "event": "Incident resolved for >99% of users. Long-tail recovery (24h TTL resolvers) continues."}
    ],
    "alerts": [
        {
            "alert_id": "ALT-601", "service": "dns-health-check",
            "severity": "critical",
            "message": "Health check failure: api.example.com NXDOMAIN from 14/14 probe locations.",
            "timestamp": "2024-04-03T08:47:00Z",
            "tags": {"env": "prod"}, "is_root_cause": True, "acknowledged": True
        }
    ],
    "logs": [],
    "topology": {
        "services": {
            "route53":    {"upstream": [], "downstream": ["api-gateway", "app-frontend"], "healthy": False},
            "api-gateway": {"upstream": ["route53"], "downstream": [], "healthy": False},
            "app-frontend": {"upstream": ["route53"], "downstream": [], "healthy": False}
        }
    },
    "ground_truth": {
        "required_sections": ["impact_summary", "timeline", "root_cause", "contributing_factors", "action_items", "lessons_learned"],
        "expected_root_cause_keywords": ["ttl", "nameserver", "route53", "propagation", "dns", "86400", "migration"],
        "expected_contributing_factors": [
            "TTL set to 86400 instead of 300 on new nameserver",
            "old nameserver decommissioned before propagation confirmed",
            "no dns propagation check in migration runbook",
            "no rollback plan once old nameserver decommissioned"
        ],
        "required_action_item_themes": ["ttl validation", "propagation check", "runbook", "rollback plan"],
        "minimum_timeline_events": 8,
        "minimum_action_items": 3
    }
})


# ---------------------------------------------------------------------------
# Additional scenarios — Task 1 (easy): 2 more diverse failure modes
# ---------------------------------------------------------------------------

ALERT_CLASSIFICATION_SCENARIOS.append({
    "id": "sc-ac-004",
    "description": "Kafka consumer lag spike — dead letter queue overflow causes downstream data loss",
    "alerts": [
        {
            "alert_id": "ALT-601", "service": "kafka-broker",
            "severity": "critical", "is_root_cause": True,
            "message": "Kafka broker kafka-prod-02 leader election failed. Partition 0,1,2 of topic events.payments offline for 94s.",
            "timestamp": "2024-04-05T22:10:03Z",
            "tags": {"env": "prod", "topic": "events.payments", "broker": "kafka-prod-02"}
        },
        {
            "alert_id": "ALT-602", "service": "payment-consumer",
            "severity": "critical", "is_root_cause": False,
            "message": "Payment consumer group lag: 847,221 messages behind. Consumer group payment-processor-v2 stalled.",
            "timestamp": "2024-04-05T22:10:45Z",
            "tags": {"env": "prod", "consumer_group": "payment-processor-v2"}
        },
        {
            "alert_id": "ALT-603", "service": "dead-letter-queue",
            "severity": "high", "is_root_cause": False,
            "message": "Dead letter queue depth: 12,004 (capacity: 10,000). Messages being dropped.",
            "timestamp": "2024-04-05T22:11:30Z",
            "tags": {"env": "prod"}
        },
        {
            "alert_id": "ALT-604", "service": "ledger-service",
            "severity": "high", "is_root_cause": False,
            "message": "Ledger reconciliation stalled. No new payment events received for 7m32s.",
            "timestamp": "2024-04-05T22:12:00Z",
            "tags": {"env": "prod"}
        },
        {
            "alert_id": "ALT-605", "service": "reporting-dashboard",
            "severity": "low", "is_root_cause": False,
            "message": "Real-time payment reporting dashboard data stale by >8 minutes.",
            "timestamp": "2024-04-05T22:12:30Z",
            "tags": {"env": "prod"}
        }
    ],
    "logs": [
        {
            "timestamp": "2024-04-05T22:09:58Z", "service": "kafka-broker",
            "level": "ERROR",
            "message": "kafka-prod-02 lost ZooKeeper session (session timeout: 6000ms). Initiating leader re-election for 3 partitions.",
            "trace_id": None
        },
        {
            "timestamp": "2024-04-05T22:10:05Z", "service": "payment-consumer",
            "level": "ERROR",
            "message": "LEADER_NOT_AVAILABLE for partition events.payments-0. Backoff 500ms, retry 1/10.",
            "trace_id": "trace-k1b2c"
        },
        {
            "timestamp": "2024-04-05T22:10:44Z", "service": "payment-consumer",
            "level": "ERROR",
            "message": "Consumer poll timeout after 30000ms. Triggering rebalance. Group: payment-processor-v2",
            "trace_id": None
        }
    ],
    "topology": {
        "services": {
            "kafka-broker":       {"upstream": ["zookeeper"], "downstream": ["payment-consumer"], "healthy": False},
            "payment-consumer":   {"upstream": ["kafka-broker"], "downstream": ["ledger-service", "dead-letter-queue"], "healthy": False},
            "dead-letter-queue":  {"upstream": ["payment-consumer"], "downstream": [], "healthy": False},
            "ledger-service":     {"upstream": ["payment-consumer"], "downstream": ["reporting-dashboard"], "healthy": False},
            "reporting-dashboard": {"upstream": ["ledger-service"], "downstream": [], "healthy": False},
            "zookeeper":          {"upstream": [], "downstream": ["kafka-broker"], "healthy": True}
        }
    },
    "ground_truth": {
        "root_cause_alert_id": "ALT-601",
        "root_cause_service": "kafka-broker",
        "blast_radius": ["payment-consumer", "dead-letter-queue", "ledger-service", "reporting-dashboard"],
        "correct_severity_map": {
            "ALT-601": "critical", "ALT-602": "critical",
            "ALT-603": "high", "ALT-604": "high", "ALT-605": "low"
        }
    }
})

ALERT_CLASSIFICATION_SCENARIOS.append({
    "id": "sc-ac-005",
    "description": "Elasticsearch disk watermark breach causing cluster-wide index rejection",
    "alerts": [
        {
            "alert_id": "ALT-701", "service": "elasticsearch-node-03",
            "severity": "critical", "is_root_cause": True,
            "message": "Elasticsearch node es-prod-03 disk usage 95.2% (flood-stage watermark: 95%). All indices on node set to read-only.",
            "timestamp": "2024-04-06T08:33:15Z",
            "tags": {"env": "prod", "node": "es-prod-03", "disk_used_pct": "95.2"}
        },
        {
            "alert_id": "ALT-702", "service": "elasticsearch-cluster",
            "severity": "critical", "is_root_cause": False,
            "message": "Elasticsearch cluster status RED. Shard allocation blocked on 14 indices. Write operations failing cluster-wide.",
            "timestamp": "2024-04-06T08:33:40Z",
            "tags": {"env": "prod"}
        },
        {
            "alert_id": "ALT-703", "service": "search-api",
            "severity": "high", "is_root_cause": False,
            "message": "Search API write error rate: 100% (index operations rejected). Read traffic unaffected.",
            "timestamp": "2024-04-06T08:34:00Z",
            "tags": {"env": "prod"}
        },
        {
            "alert_id": "ALT-704", "service": "log-ingestion-pipeline",
            "severity": "high", "is_root_cause": False,
            "message": "Log ingestion pipeline backing up. 2.3M events queued, unable to write to Elasticsearch.",
            "timestamp": "2024-04-06T08:34:30Z",
            "tags": {"env": "prod"}
        },
        {
            "alert_id": "ALT-705", "service": "audit-service",
            "severity": "medium", "is_root_cause": False,
            "message": "Audit log writes failing. Compliance risk: audit trail gap starting 08:33:15Z.",
            "timestamp": "2024-04-06T08:35:00Z",
            "tags": {"env": "prod"}
        }
    ],
    "logs": [
        {
            "timestamp": "2024-04-06T08:33:10Z", "service": "elasticsearch-node-03",
            "level": "ERROR",
            "message": "flood stage disk watermark [95%] exceeded on [es-prod-03], all indices on this node will be marked read-only",
            "trace_id": None
        },
        {
            "timestamp": "2024-04-06T08:33:35Z", "service": "elasticsearch-cluster",
            "level": "ERROR",
            "message": "blocked by: [FORBIDDEN/12/index read-only / allow delete (api)]; index [logs-2024.04.06] blocked",
            "trace_id": None
        },
        {
            "timestamp": "2024-04-06T08:30:00Z", "service": "elasticsearch-node-03",
            "level": "WARN",
            "message": "high disk watermark [90%] exceeded on [es-prod-03]. Shards will be relocated away from this node. disk usage: 91.8%",
            "trace_id": None
        }
    ],
    "topology": {
        "services": {
            "elasticsearch-node-03":  {"upstream": [], "downstream": ["elasticsearch-cluster"], "healthy": False},
            "elasticsearch-cluster":  {"upstream": ["elasticsearch-node-03"], "downstream": ["search-api", "log-ingestion-pipeline", "audit-service"], "healthy": False},
            "search-api":             {"upstream": ["elasticsearch-cluster"], "downstream": [], "healthy": False},
            "log-ingestion-pipeline": {"upstream": ["elasticsearch-cluster"], "downstream": [], "healthy": False},
            "audit-service":          {"upstream": ["elasticsearch-cluster"], "downstream": [], "healthy": False}
        }
    },
    "ground_truth": {
        "root_cause_alert_id": "ALT-701",
        "root_cause_service": "elasticsearch-node-03",
        "blast_radius": ["elasticsearch-cluster", "search-api", "log-ingestion-pipeline", "audit-service"],
        "correct_severity_map": {
            "ALT-701": "critical", "ALT-702": "critical",
            "ALT-703": "high", "ALT-704": "high", "ALT-705": "medium"
        }
    }
})


# ---------------------------------------------------------------------------
# Additional scenarios — Task 2 (medium): 2 more multi-hop RCA scenarios
# ---------------------------------------------------------------------------

ROOT_CAUSE_SCENARIOS.append({
    "id": "sc-rca-004",
    "description": "Clock skew between nodes causes distributed lock starvation and payment deduplication failure",
    "alerts": [
        {
            "alert_id": "ALT-801", "service": "payment-dedup-service",
            "severity": "critical", "is_root_cause": False,
            "message": "Payment deduplication lock acquisition timeout rate: 78%. Duplicate payments being processed.",
            "timestamp": "2024-04-07T15:22:10Z",
            "tags": {"env": "prod"}
        },
        {
            "alert_id": "ALT-802", "service": "ntp-sync",
            "severity": "critical", "is_root_cause": True,
            "message": "NTP sync failure on payment-worker-04, payment-worker-05. Clock drift: +8.4 seconds vs cluster average.",
            "timestamp": "2024-04-07T15:20:05Z",
            "tags": {"env": "prod", "nodes": "payment-worker-04,payment-worker-05", "drift_s": "8.4"}
        },
        {
            "alert_id": "ALT-803", "service": "distributed-lock-service",
            "severity": "high", "is_root_cause": False,
            "message": "Redlock TTL expiry anomaly: locks acquired on payment-worker-04 expiring 8.4s early. Race condition window open.",
            "timestamp": "2024-04-07T15:22:00Z",
            "tags": {"env": "prod"}
        },
        {
            "alert_id": "ALT-804", "service": "payment-service",
            "severity": "high", "is_root_cause": False,
            "message": "Duplicate payment transactions detected: 143 in last 10 minutes. Idempotency keys not preventing duplicates.",
            "timestamp": "2024-04-07T15:23:00Z",
            "tags": {"env": "prod"}
        }
    ],
    "logs": [
        {
            "timestamp": "2024-04-07T15:19:50Z", "service": "ntp-sync",
            "level": "ERROR",
            "message": "ntpd on payment-worker-04: Unable to sync with NTP pool. Last sync: 2024-04-07T11:34:00Z (3h46m ago). Current drift: +8391ms",
            "trace_id": None
        },
        {
            "timestamp": "2024-04-07T15:20:30Z", "service": "distributed-lock-service",
            "level": "WARN",
            "message": "Lock payment-dedup:txn_4829a acquired on payment-worker-04 with TTL=10000ms. Due to clock skew, effective TTL on other nodes is ~1600ms. Early expiry likely.",
            "trace_id": None
        },
        {
            "timestamp": "2024-04-07T15:21:45Z", "service": "payment-dedup-service",
            "level": "ERROR",
            "message": "Dedup lock for idempotency_key=idem_8821a expired before payment commit. Second worker acquired same lock. Duplicate payment risk.",
            "trace_id": "trace-d8f2a"
        },
        {
            "timestamp": "2024-04-07T15:22:05Z", "service": "payment-service",
            "level": "ERROR",
            "message": "Duplicate payment detected: transaction_id=txn_4829a processed twice. Amounts: $142.50 + $142.50. Customer: cust_9981.",
            "trace_id": "trace-e9g3b"
        }
    ],
    "topology": {
        "services": {
            "ntp-sync":                {"upstream": [], "downstream": ["payment-worker-04", "payment-worker-05"], "healthy": False},
            "payment-worker-04":       {"upstream": ["ntp-sync"], "downstream": ["distributed-lock-service", "payment-dedup-service"], "healthy": False},
            "payment-worker-05":       {"upstream": ["ntp-sync"], "downstream": ["distributed-lock-service"], "healthy": False},
            "distributed-lock-service": {"upstream": ["payment-worker-04", "payment-worker-05"], "downstream": ["payment-dedup-service"], "healthy": False},
            "payment-dedup-service":   {"upstream": ["distributed-lock-service"], "downstream": ["payment-service"], "healthy": False},
            "payment-service":         {"upstream": ["payment-dedup-service"], "downstream": [], "healthy": False}
        }
    },
    "ground_truth": {
        "root_cause_alert_id": "ALT-802",
        "root_cause_service": "ntp-sync",
        "root_cause_description": "NTP sync failed on payment-worker-04 and payment-worker-05, causing an 8.4-second clock drift. The Redlock distributed locking algorithm depends on wall-clock agreement between nodes. The clock skew caused locks acquired on drifted nodes to expire ~8 seconds early on other nodes, opening a race condition window where two workers simultaneously held the payment deduplication lock, resulting in duplicate payment processing.",
        "causal_chain": [
            "NTP sync fails on payment-worker-04 and 05 — clock drifts +8.4 seconds",
            "Redlock TTL calculated using local wall clock — locks set with TTL=10s",
            "Other nodes see effective TTL of ~1.6s due to clock skew",
            "Deduplication lock expires before payment transaction commits",
            "Second worker acquires same dedup lock — race condition opens",
            "Same payment processed twice — 143 duplicate transactions in 10 minutes"
        ],
        "contributing_factors": [
            "No NTP drift alerting threshold configured (drift grew for 3h46m undetected)",
            "Redlock implementation did not validate clock skew between nodes before acquiring locks",
            "No idempotency check at the database layer as fallback to application-level dedup"
        ]
    }
})

ROOT_CAUSE_SCENARIOS.append({
    "id": "sc-rca-005",
    "description": "Disk I/O saturation from runaway log rotation causing cascading write timeouts",
    "alerts": [
        {
            "alert_id": "ALT-901", "service": "app-server-07",
            "severity": "critical", "is_root_cause": True,
            "message": "app-server-07 disk I/O wait: 94% (threshold: 20%). /var/log volume write latency: 18,400ms.",
            "timestamp": "2024-04-08T03:14:10Z",
            "tags": {"env": "prod", "host": "app-server-07"}
        },
        {
            "alert_id": "ALT-902", "service": "order-service",
            "severity": "critical", "is_root_cause": False,
            "message": "Order service write timeout rate: 89%. Database writes completing but local logging blocking thread pool.",
            "timestamp": "2024-04-08T03:14:35Z",
            "tags": {"env": "prod"}
        },
        {
            "alert_id": "ALT-903", "service": "audit-log-service",
            "severity": "high", "is_root_cause": False,
            "message": "Audit log write latency: 22s avg (SLO: 200ms). 8,400 audit events queued.",
            "timestamp": "2024-04-08T03:15:00Z",
            "tags": {"env": "prod"}
        },
        {
            "alert_id": "ALT-904", "service": "api-gateway",
            "severity": "high", "is_root_cause": False,
            "message": "API gateway P99 latency: 28,000ms. Thread pool exhausted waiting for order-service.",
            "timestamp": "2024-04-08T03:15:20Z",
            "tags": {"env": "prod"}
        }
    ],
    "logs": [
        {
            "timestamp": "2024-04-08T03:13:45Z", "service": "app-server-07",
            "level": "WARN",
            "message": "logrotate: /var/log/app/*.log — 847 files compressed simultaneously. gzip CPU+IO spike. Duration so far: 47s.",
            "trace_id": None
        },
        {
            "timestamp": "2024-04-08T03:13:50Z", "service": "app-server-07",
            "level": "ERROR",
            "message": "iostat: /dev/sda1 util=97.4% await=18421ms. Write queue depth: 2,847. Device saturated.",
            "trace_id": None
        },
        {
            "timestamp": "2024-04-08T03:14:08Z", "service": "order-service",
            "level": "ERROR",
            "message": "log4j AsyncAppender queue full (capacity: 128). Blocking application thread for write. Thread: order-handler-pool-12.",
            "trace_id": "trace-r4s5t"
        },
        {
            "timestamp": "2024-04-08T03:14:30Z", "service": "order-service",
            "level": "ERROR",
            "message": "Thread pool order-handler-pool exhausted: 200/200 threads blocked on log flush. New requests queuing.",
            "trace_id": None
        },
        {
            "timestamp": "2024-04-08T03:13:40Z", "service": "app-server-07",
            "level": "INFO",
            "message": "cron: logrotate daily job started. Config: compress, delaycompress, missingok. Rotating 847 log files.",
            "trace_id": None
        }
    ],
    "topology": {
        "services": {
            "app-server-07":   {"upstream": [], "downstream": ["order-service", "audit-log-service"], "healthy": False},
            "order-service":   {"upstream": ["app-server-07"], "downstream": ["api-gateway"], "healthy": False},
            "audit-log-service": {"upstream": ["app-server-07"], "downstream": [], "healthy": False},
            "api-gateway":     {"upstream": ["order-service"], "downstream": [], "healthy": False}
        }
    },
    "ground_truth": {
        "root_cause_alert_id": "ALT-901",
        "root_cause_service": "app-server-07",
        "root_cause_description": "The daily logrotate cron job fired at 03:13 and attempted to simultaneously compress 847 log files with gzip. This saturated the disk I/O on app-server-07 (/dev/sda1 at 97.4% utilisation, 18s write latency). The order-service log4j AsyncAppender's write queue filled, causing application threads to block on log flush. With all 200 threads blocked on I/O, the order-service became unable to handle new requests, cascading to api-gateway thread exhaustion.",
        "causal_chain": [
            "Daily logrotate cron job starts — compresses 847 log files simultaneously",
            "/dev/sda1 I/O utilisation reaches 97.4%, write latency 18,421ms",
            "log4j AsyncAppender write queue fills (128/128 capacity)",
            "Application threads block waiting for log flush — order-handler-pool exhausted",
            "order-service unable to process new requests — API gateway times out"
        ],
        "contributing_factors": [
            "logrotate configured to compress all logs simultaneously instead of one at a time (missing sharedscripts + postrotate signal)",
            "log4j AsyncAppender configured in blocking mode — should use DISCARD policy under I/O pressure",
            "No I/O rate limiting on logrotate (missing ionice / iorate config)",
            "847 log files accumulated — log retention policy too permissive"
        ]
    }
})


# ---------------------------------------------------------------------------
# Additional scenarios — Task 3 (hard): 2 more postmortem scenarios
# ---------------------------------------------------------------------------

POSTMORTEM_SCENARIOS.append({
    "id": "sc-pm-004",
    "description": "Kafka broker ZooKeeper session loss causing 28-minute payment consumer stall",
    "incident_summary": {
        "title": "Payment Consumer Stall Due to Kafka Broker Leader Election Failure — 2024-04-05",
        "duration_minutes": 28,
        "start_time": "2024-04-05T22:10:03Z",
        "end_time": "2024-04-05T22:38:07Z",
        "affected_services": ["kafka-broker", "payment-consumer", "ledger-service", "dead-letter-queue"],
        "user_impact": "~47,000 payment events unprocessed for 28 minutes. Dead letter queue overflowed, dropping 2,004 events. Ledger reconciliation delayed 35 minutes.",
        "severity": "SEV-1"
    },
    "timeline": [
        {"time": "22:09:58Z", "event": "kafka-prod-02 loses ZooKeeper session due to GC pause exceeding session timeout (6000ms)"},
        {"time": "22:10:03Z", "event": "Leader re-election initiated for 3 partitions of events.payments topic"},
        {"time": "22:10:03Z", "event": "PagerDuty alert: Kafka broker leader election failure"},
        {"time": "22:10:45Z", "event": "Payment consumer group stalls — LEADER_NOT_AVAILABLE errors"},
        {"time": "22:11:00Z", "event": "On-call engineer (Eve) acknowledges alert"},
        {"time": "22:11:30Z", "event": "Dead letter queue depth exceeds 10,000 capacity — events being dropped"},
        {"time": "22:14:00Z", "event": "Eve identifies kafka-prod-02 GC logs: 8.2s stop-the-world pause caused ZK session drop"},
        {"time": "22:18:00Z", "event": "Decision: restart kafka-prod-02 broker with increased ZK session timeout (30000ms)"},
        {"time": "22:20:00Z", "event": "kafka-prod-02 restarted. Leader election completes in 4s."},
        {"time": "22:21:00Z", "event": "Payment consumer group rebalancing. Lag: 847,221 messages."},
        {"time": "22:35:00Z", "event": "Consumer lag reduces to <10,000. Processing rate back to normal."},
        {"time": "22:38:07Z", "event": "Incident resolved. 2,004 events in dead letter queue require manual replay."}
    ],
    "alerts": [
        {
            "alert_id": "ALT-601", "service": "kafka-broker", "severity": "critical",
            "message": "Kafka broker kafka-prod-02 leader election failed. Partitions offline.",
            "timestamp": "2024-04-05T22:10:03Z",
            "tags": {"env": "prod"}, "is_root_cause": True, "acknowledged": True
        }
    ],
    "logs": [],
    "topology": {
        "services": {
            "kafka-broker":     {"upstream": ["zookeeper"], "downstream": ["payment-consumer"], "healthy": False},
            "payment-consumer": {"upstream": ["kafka-broker"], "downstream": ["ledger-service"], "healthy": False},
            "ledger-service":   {"upstream": ["payment-consumer"], "downstream": [], "healthy": False}
        }
    },
    "ground_truth": {
        "required_sections": ["impact_summary", "timeline", "root_cause", "contributing_factors", "action_items", "lessons_learned"],
        "expected_root_cause_keywords": ["zookeeper", "session", "gc", "pause", "leader", "election", "timeout"],
        "expected_contributing_factors": [
            "zookeeper session timeout too low (6000ms) for jvm gc pauses",
            "no gc pause alerting on kafka broker jvm",
            "dead letter queue capacity too small for 28-minute backlog",
            "no automatic dead letter queue replay mechanism"
        ],
        "required_action_item_themes": ["zookeeper timeout", "gc tuning", "dead letter queue", "consumer lag alert"],
        "minimum_timeline_events": 8,
        "minimum_action_items": 3
    }
})

POSTMORTEM_SCENARIOS.append({
    "id": "sc-pm-005",
    "description": "Clock skew between payment workers caused 143 duplicate transactions over 13 minutes",
    "incident_summary": {
        "title": "Duplicate Payment Transactions Due to NTP Sync Failure and Distributed Lock Clock Skew — 2024-04-07",
        "duration_minutes": 13,
        "start_time": "2024-04-07T15:19:50Z",
        "end_time": "2024-04-07T15:32:45Z",
        "affected_services": ["payment-worker-04", "payment-worker-05", "distributed-lock-service", "payment-dedup-service"],
        "user_impact": "143 duplicate payment transactions totalling $18,420. All customers notified. Refunds issued within 2 hours. No customer data breached.",
        "severity": "SEV-1"
    },
    "timeline": [
        {"time": "11:34:00Z", "event": "Last successful NTP sync on payment-worker-04 and payment-worker-05"},
        {"time": "15:19:50Z", "event": "NTP sync alert fires: payment-worker-04/05 clock drift +8.4 seconds"},
        {"time": "15:20:30Z", "event": "First duplicate payment detected (txn_4829a processed twice)"},
        {"time": "15:22:00Z", "event": "PagerDuty alert: distributed lock TTL anomaly on payment-worker-04"},
        {"time": "15:22:10Z", "event": "On-call engineer (Frank) paged. Duplicate payment alert fires."},
        {"time": "15:24:00Z", "event": "Frank identifies clock skew as root cause from NTP logs"},
        {"time": "15:25:00Z", "event": "Mitigation: payment-worker-04 and 05 drained from load balancer"},
        {"time": "15:26:00Z", "event": "ntpdate -u pool.ntp.org run on affected nodes. Clocks corrected."},
        {"time": "15:28:00Z", "event": "Nodes added back to load balancer. Duplicate rate drops to 0."},
        {"time": "15:30:00Z", "event": "Database audit query confirms 143 duplicate transactions"},
        {"time": "15:32:45Z", "event": "Incident resolved. Finance team begins refund processing."}
    ],
    "alerts": [
        {
            "alert_id": "ALT-802", "service": "ntp-sync", "severity": "critical",
            "message": "NTP sync failure. Clock drift: +8.4s on payment-worker-04, payment-worker-05.",
            "timestamp": "2024-04-07T15:19:50Z",
            "tags": {"env": "prod"}, "is_root_cause": True, "acknowledged": True
        }
    ],
    "logs": [],
    "topology": {
        "services": {
            "ntp-sync":                 {"upstream": [], "downstream": ["payment-worker-04", "payment-worker-05"], "healthy": False},
            "payment-worker-04":        {"upstream": ["ntp-sync"], "downstream": ["distributed-lock-service"], "healthy": False},
            "distributed-lock-service": {"upstream": ["payment-worker-04", "payment-worker-05"], "downstream": ["payment-dedup-service"], "healthy": False},
            "payment-dedup-service":    {"upstream": ["distributed-lock-service"], "downstream": [], "healthy": False}
        }
    },
    "ground_truth": {
        "required_sections": ["impact_summary", "timeline", "root_cause", "contributing_factors", "action_items", "lessons_learned"],
        "expected_root_cause_keywords": ["ntp", "clock", "skew", "drift", "redlock", "ttl", "distributed lock", "deduplication"],
        "expected_contributing_factors": [
            "no ntp drift alerting for 3h46m",
            "redlock did not validate clock skew between nodes",
            "no database-level idempotency check as fallback",
            "ntp sync failure went undetected for hours"
        ],
        "required_action_item_themes": ["ntp monitoring", "clock skew validation", "database idempotency", "refund automation"],
        "minimum_timeline_events": 8,
        "minimum_action_items": 4
    }
})
