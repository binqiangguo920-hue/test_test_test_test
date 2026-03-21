"""
模拟的可观测性平台后端服务
提供两个核心能力：
  1. 查询服务健康状态 (health check)
  2. 查询最近告警 (recent alerts)
"""

import json
import random
from datetime import datetime, timedelta

# ============================================================
# 模拟数据：假设我们有3个微服务
# ============================================================
SERVICES = {
    "user-api": {
        "status": "healthy",
        "uptime": "99.97%",
        "latency_p99_ms": 42,
        "error_rate": 0.03,
        "instances": 3,
    },
    "order-service": {
        "status": "degraded",
        "uptime": "98.50%",
        "latency_p99_ms": 580,
        "error_rate": 1.52,
        "instances": 5,
    },
    "payment-gateway": {
        "status": "healthy",
        "uptime": "99.99%",
        "latency_p99_ms": 120,
        "error_rate": 0.01,
        "instances": 4,
    },
}

ALERTS = [
    {
        "id": "ALT-001",
        "service": "order-service",
        "severity": "warning",
        "message": "P99 latency exceeded 500ms threshold",
        "timestamp": (datetime.now() - timedelta(minutes=12)).isoformat(),
    },
    {
        "id": "ALT-002",
        "service": "order-service",
        "severity": "critical",
        "message": "Error rate above 1.5% for 5 minutes",
        "timestamp": (datetime.now() - timedelta(minutes=8)).isoformat(),
    },
    {
        "id": "ALT-003",
        "service": "user-api",
        "severity": "info",
        "message": "Auto-scaling triggered: 2 -> 3 instances",
        "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
    },
]


def get_service_health(service_name: str) -> dict:
    """查询指定服务的健康状态"""
    if service_name not in SERVICES:
        return {"error": f"Service '{service_name}' not found", "available": list(SERVICES.keys())}
    return {"service": service_name, **SERVICES[service_name]}


def get_recent_alerts(service_name: str = None, severity: str = None) -> list:
    """查询最近的告警，可按服务名或严重程度过滤"""
    results = ALERTS
    if service_name:
        results = [a for a in results if a["service"] == service_name]
    if severity:
        results = [a for a in results if a["severity"] == severity]
    return results


def list_services() -> list:
    """列出所有可监控的服务"""
    return [{"name": k, "status": v["status"]} for k, v in SERVICES.items()]
