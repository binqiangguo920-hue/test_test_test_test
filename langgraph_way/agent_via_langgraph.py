#!/usr/bin/env python3
"""
===== LangGraph Agent 调用 CLI 工具 =====

核心思路：用 @tool 装饰器把 CLI 命令包装成 LangGraph 能识别的 Tool，
LLM 就能自动决定何时调用、传什么参数。

有两种包装方式：
  方式A: subprocess 调用外部 CLI 脚本（通用，适合任何 CLI）
  方式B: 直接 import Python 函数（同语言时更简洁）

安装依赖:
  pip install langgraph langchain-anthropic
"""

import subprocess
import json
import os
import sys

# ============================================================
# 方式A: 用 subprocess 包装 CLI 工具（通用方式）
# 适用于：任何语言写的 CLI 工具（Go/Rust/Python/Shell）
# ============================================================

# --- 如果安装了 langchain，使用真实的 @tool ---
try:
    from langchain_core.tools import tool

    CLI_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "cli_way", "obs_cli.py")

    @tool
    def check_service_health(service_name: str) -> str:
        """查询指定微服务的健康状态，包括 uptime、延迟、错误率。
        Args:
            service_name: 服务名称，如 'order-service', 'user-api', 'payment-gateway'
        """
        result = subprocess.run(
            ["python3", CLI_SCRIPT, "health", service_name],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        return result.stdout

    @tool
    def get_alerts(service_name: str = None, severity: str = None) -> str:
        """查询最近的告警信息，可按服务名和严重程度过滤。
        Args:
            service_name: 按服务名过滤（可选）
            severity: 按严重程度过滤，可选值: info, warning, critical（可选）
        """
        cmd = ["python3", CLI_SCRIPT, "alerts"]
        if service_name:
            cmd += ["--service", service_name]
        if severity:
            cmd += ["--severity", severity]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        return result.stdout

    @tool
    def list_all_services() -> str:
        """列出所有可监控的微服务及其当前状态。"""
        result = subprocess.run(
            ["python3", CLI_SCRIPT, "list-services"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        return result.stdout

    TOOLS = [check_service_health, get_alerts, list_all_services]
    HAS_LANGCHAIN = True

except ImportError:
    HAS_LANGCHAIN = False
    TOOLS = []


# ============================================================
# 方式B: 直接 import Python 函数（同语言简洁方式）
# 适用于：后端也是 Python 时，省去 subprocess 开销
# ============================================================

if HAS_LANGCHAIN:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from backend.observability_service import (
        get_service_health as _get_health,
        get_recent_alerts as _get_alerts,
        list_services as _list_svc,
    )

    @tool
    def check_service_health_direct(service_name: str) -> str:
        """查询指定微服务的健康状态（直接调用，无 subprocess 开销）。
        Args:
            service_name: 服务名称
        """
        return json.dumps(_get_health(service_name), indent=2)

    # 直接调用方式的工具列表
    TOOLS_DIRECT = [check_service_health_direct]


# ============================================================
# 完整的 LangGraph Agent 构建
# ============================================================

def build_and_run_agent():
    """构建一个完整的 LangGraph ReAct Agent 并运行"""
    if not HAS_LANGCHAIN:
        print("需要安装依赖: pip install langgraph langchain-anthropic")
        print("下面展示伪代码流程:\n")
        show_pseudocode()
        return

    from langgraph.prebuilt import create_react_agent
    from langchain_anthropic import ChatAnthropic

    # 1. 创建 LLM
    llm = ChatAnthropic(model="claude-sonnet-4-20250514")

    # 2. 创建 Agent（把 CLI 工具传进去）
    agent = create_react_agent(llm, tools=TOOLS)

    # 3. 运行 Agent
    result = agent.invoke({
        "messages": [
            ("user", "帮我检查一下所有服务的健康状态，如果有异常的服务，查一下它的告警信息并给出诊断建议。")
        ]
    })

    for msg in result["messages"]:
        print(f"[{msg.type}] {msg.content}")


def show_pseudocode():
    """展示不安装依赖时的伪代码流程"""
    print("""
# ============================================================
# LangGraph Agent 调用 CLI 工具的完整流程（伪代码）
# ============================================================

# Step 1: 定义工具 —— 用 @tool 把 CLI 包装成结构化函数
# ─────────────────────────────────────────────────────────────

from langchain_core.tools import tool

@tool
def check_service_health(service_name: str) -> str:
    \"\"\"查询指定微服务的健康状态。\"\"\"          # ← docstring 变成工具描述
    result = subprocess.run(                      # ← subprocess 调用 CLI
        ["python3", "obs_cli.py", "health", service_name],
        capture_output=True, text=True,
    )
    return result.stdout                          # ← 返回值给 LLM 看

@tool
def get_alerts(service_name: str = None, severity: str = None) -> str:
    \"\"\"查询最近的告警信息。\"\"\"
    cmd = ["python3", "obs_cli.py", "alerts"]
    if service_name:
        cmd += ["--service", service_name]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


# Step 2: 创建 Agent —— 把工具列表传给 LangGraph
# ─────────────────────────────────────────────────────────────

from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(model="claude-sonnet-4-20250514")
agent = create_react_agent(llm, tools=[check_service_health, get_alerts])


# Step 3: 运行 —— LLM 自动决定调用哪些工具
# ─────────────────────────────────────────────────────────────

result = agent.invoke({
    "messages": [("user", "检查 order-service 的状态和告警")]
})

# LLM 会自动:
#   1. 调用 check_service_health("order-service")  → 拿到健康数据
#   2. 发现 status=degraded，决定调用 get_alerts("order-service")
#   3. 综合两次结果，生成诊断报告


# ============================================================
# 完整的调用链路:
#
#   用户提问
#     ↓
#   LLM 分析 → 决定调用 check_service_health
#     ↓
#   LangGraph 执行 @tool 函数
#     ↓
#   subprocess.run("obs_cli.py health order-service")
#     ↓
#   CLI 输出 JSON 文本 → 返回给 LLM
#     ↓
#   LLM 分析结果 → 决定调用 get_alerts
#     ↓
#   subprocess.run("obs_cli.py alerts --service order-service")
#     ↓
#   LLM 综合所有结果 → 输出诊断报告给用户
# ============================================================
""")


# ============================================================
# 对比：LangGraph 调 CLI vs Claude Code 调 CLI
# ============================================================

def show_comparison():
    print("""
╔══════════════════════════════════════════════════════════════╗
║  对比：LangGraph 调 CLI  vs  Claude Code 调 CLI             ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  LangGraph Agent:                                            ║
║    @tool 装饰器 → LLM function calling → subprocess → CLI   ║
║    · 你需要自己写 @tool 包装函数                              ║
║    · 你控制 Agent 的推理循环（ReAct/自定义 Graph）            ║
║    · subprocess 调 CLI，解析 stdout                          ║
║                                                              ║
║  Claude Code Agent:                                          ║
║    Bash tool → subprocess → CLI                              ║
║    · Claude Code 已有内置的 Bash tool                        ║
║    · LLM 直接生成 shell 命令并执行                            ║
║    · 同样是 subprocess，但不需要你写包装代码                  ║
║                                                              ║
║  核心区别:                                                    ║
║    LangGraph = 你自己搭 Agent 框架，自己包装工具              ║
║    Claude Code = 已有 Agent 框架，Bash tool 开箱即用          ║
║                                                              ║
║  共同问题:                                                    ║
║    都是 subprocess 调 CLI → 文本解析，                        ║
║    都不如 MCP 的结构化协议优雅。                               ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    show_pseudocode()
    show_comparison()
    print("\n如果已安装 langgraph + langchain-anthropic，取消下面的注释即可运行:")
    print("  build_and_run_agent()")
