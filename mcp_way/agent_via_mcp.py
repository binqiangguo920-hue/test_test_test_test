#!/usr/bin/env python3
"""
===== Agent 通过 MCP 方式调用可观测性工具 =====

核心流程:
  1. Agent 启动 MCP Server（一次性，长连接）
  2. 调用 tools/list 发现可用工具及其 schema
  3. 调用 tools/call 执行工具，传入结构化参数
  4. 接收结构化结果，直接使用

优势用 ✅ 标注
"""

import subprocess
import json
import os

MCP_SERVER = os.path.join(os.path.dirname(__file__), "obs_mcp_server.py")


class MCPClient:
    """模拟 MCP Client：通过 stdio 与 MCP Server 通信"""

    def __init__(self, server_script: str):
        # ✅ 优势1: 只启动一次进程，保持长连接
        self.process = subprocess.Popen(
            ["python3", server_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._req_id = 0
        # 初始化握手
        self._send({"method": "initialize", "params": {}})

    def _send(self, request: dict) -> dict:
        self._req_id += 1
        request["jsonrpc"] = "2.0"
        request["id"] = self._req_id
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        response_line = self.process.stdout.readline()
        return json.loads(response_line)

    def list_tools(self) -> list:
        """✅ 优势2: Agent 可以自动发现所有可用工具及其参数 schema"""
        resp = self._send({"method": "tools/list", "params": {}})
        return resp["result"]["tools"]

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """✅ 优势3: 结构化的参数传递，不需要拼命令行字符串"""
        resp = self._send({
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        })
        result = resp["result"]
        # ✅ 优势4: 可以检查 isError 字段，错误处理标准化
        if result.get("isError"):
            raise RuntimeError(f"Tool error: {result['content'][0]['text']}")
        return json.loads(result["content"][0]["text"])

    def close(self):
        self.process.stdin.close()
        self.process.wait()


def agent_workflow():
    """模拟 Agent 的相同工作流：诊断 order-service 的问题"""
    print("=" * 60)
    print("Agent Workflow (MCP 方式)")
    print("=" * 60)

    client = MCPClient(MCP_SERVER)

    # ✅ 优势5: Agent 可以先发现有哪些工具
    print("\n--- Step 0: 自动发现可用工具 ---")
    tools = client.list_tools()
    for t in tools:
        print(f"  🔧 {t['name']}: {t['description']}")

    # Step 1: 列出所有服务
    print("\n--- Step 1: 列出所有服务 ---")
    # ✅ 对比 CLI: 不需要拼 ["list-services"]，直接传工具名
    services = client.call_tool("list_services", {})
    print(f"[Agent] 发现 {len(services)} 个服务")

    # Step 2: 找到异常服务
    degraded = [s for s in services if s["status"] != "healthy"]
    if not degraded:
        print("[Agent] 所有服务正常，结束。")
        client.close()
        return

    target = degraded[0]["name"]
    print(f"\n--- Step 2: 发现异常服务 '{target}'，查询详细健康状态 ---")
    # ✅ 对比 CLI: 参数是 dict，不需要担心 shell 转义/引号问题
    health = client.call_tool("get_service_health", {"service_name": target})
    print(f"[Agent] 健康详情: status={health['status']}, "
          f"latency_p99={health['latency_p99_ms']}ms, "
          f"error_rate={health['error_rate']}%")

    # Step 3: 查询该服务的告警
    print(f"\n--- Step 3: 查询 '{target}' 的告警 ---")
    # ✅ 对比 CLI: 参数有 schema 校验，传错了会有明确错误
    alerts = client.call_tool("get_recent_alerts", {"service_name": target})
    print(f"[Agent] 发现 {len(alerts)} 条告警:")
    for alert in alerts:
        print(f"  [{alert['severity'].upper()}] {alert['message']}")

    # Step 4: Agent 做出诊断
    print(f"\n--- Step 4: Agent 综合诊断 ---")
    critical_alerts = [a for a in alerts if a["severity"] == "critical"]
    print(f"[Agent] 诊断结论: {target} 存在 {len(critical_alerts)} 个严重告警，"
          f"P99延迟 {health['latency_p99_ms']}ms 超出阈值，建议扩容。")

    client.close()


if __name__ == "__main__":
    agent_workflow()
