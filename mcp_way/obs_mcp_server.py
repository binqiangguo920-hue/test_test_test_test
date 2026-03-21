#!/usr/bin/env python3
"""
===== MCP 方式 =====
MCP Server：通过标准化的 JSON-RPC 协议暴露可观测性工具。

Agent 不再需要"拼命令行 -> 起进程 -> 解析文本"，
而是直接调用结构化的 Tool，参数和返回值都有 schema。

本文件模拟 MCP Server 的核心行为（不依赖真实 MCP SDK，
便于理解协议本质）。
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.observability_service import get_service_health, get_recent_alerts, list_services


# ============================================================
# MCP Tool 定义：每个工具有 name, description, inputSchema
# 这就是 Agent "看到"的工具列表（类比 OpenAI function calling）
# ============================================================
TOOLS = [
    {
        "name": "get_service_health",
        "description": "查询指定微服务的健康状态，包括 uptime、延迟、错误率等",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "要查询的服务名称，如 'order-service'"
                }
            },
            "required": ["service_name"]
        }
    },
    {
        "name": "get_recent_alerts",
        "description": "查询最近的告警信息，可按服务名和严重程度过滤",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "按服务名过滤（可选）"
                },
                "severity": {
                    "type": "string",
                    "enum": ["info", "warning", "critical"],
                    "description": "按严重程度过滤（可选）"
                }
            }
        }
    },
    {
        "name": "list_services",
        "description": "列出所有可监控的服务及其当前状态",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
]


# ============================================================
# MCP 消息处理（模拟 JSON-RPC over stdio）
# ============================================================
def handle_request(request: dict) -> dict:
    """处理一个 MCP JSON-RPC 请求"""
    method = request.get("method")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "serverInfo": {"name": "observability-mcp-server", "version": "1.0.0"},
                "capabilities": {"tools": {}},
            },
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS},
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        return _call_tool(req_id, tool_name, arguments)

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"},
        }


def _call_tool(req_id, tool_name: str, arguments: dict) -> dict:
    """执行工具调用并返回结构化结果"""
    try:
        if tool_name == "get_service_health":
            result = get_service_health(arguments["service_name"])
        elif tool_name == "get_recent_alerts":
            result = get_recent_alerts(
                arguments.get("service_name"),
                arguments.get("severity"),
            )
        elif tool_name == "list_services":
            result = list_services()
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"},
            }

        # ✅ 关键区别：返回的是结构化的 content，而不是纯文本
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {"type": "text", "text": json.dumps(result, indent=2, default=str)}
                ]
            },
        }

    except Exception as e:
        # ✅ 错误也是结构化的，Agent 可以程序化处理
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": str(e)}],
                "isError": True,
            },
        }


def run_stdio_server():
    """以 stdio 模式运行 MCP Server（每行一个 JSON-RPC 消息）"""
    print("[MCP Server] Observability MCP Server started (stdio mode)", file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError:
            error_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            sys.stdout.write(json.dumps(error_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_server()
