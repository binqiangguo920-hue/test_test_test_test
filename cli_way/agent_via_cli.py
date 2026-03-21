#!/usr/bin/env python3
"""
===== Agent 通过 CLI 方式调用可观测性工具 =====

核心流程:
  1. Agent 决定要调用哪个命令
  2. 拼接命令行字符串
  3. subprocess 执行，捕获 stdout
  4. 解析 JSON 文本为 Python 对象
  5. Agent 基于结果做下一步决策

问题暴露点用 ⚠️ 标注
"""

import subprocess
import json
import os

CLI_SCRIPT = os.path.join(os.path.dirname(__file__), "obs_cli.py")


def agent_call_cli(command: list[str]) -> dict | list:
    """Agent 执行一次 CLI 调用"""
    full_cmd = ["python3", CLI_SCRIPT] + command
    print(f"[Agent] 执行命令: {' '.join(full_cmd)}")

    # ⚠️ 问题1: 需要处理进程生命周期
    result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=10)

    if result.returncode != 0:
        # ⚠️ 问题2: 错误信息是无结构的 stderr 文本，Agent 难以程序化处理
        raise RuntimeError(f"CLI failed (exit {result.returncode}): {result.stderr}")

    # ⚠️ 问题3: 必须假设输出格式是 JSON，如果 CLI 输出了意外文本就会崩溃
    return json.loads(result.stdout)


def agent_workflow():
    """模拟 Agent 的一个工作流：诊断 order-service 的问题"""
    print("=" * 60)
    print("Agent Workflow (CLI 方式)")
    print("=" * 60)

    # Step 1: 列出所有服务
    print("\n--- Step 1: 列出所有服务 ---")
    services = agent_call_cli(["list-services"])
    print(f"[Agent] 发现 {len(services)} 个服务")

    # Step 2: 找到异常服务
    degraded = [s for s in services if s["status"] != "healthy"]
    if not degraded:
        print("[Agent] 所有服务正常，结束。")
        return

    target = degraded[0]["name"]
    print(f"\n--- Step 2: 发现异常服务 '{target}'，查询详细健康状态 ---")

    # ⚠️ 问题4: 每次调用都是一个新进程，无法复用连接/上下文
    health = agent_call_cli(["health", target])
    print(f"[Agent] 健康详情: status={health['status']}, "
          f"latency_p99={health['latency_p99_ms']}ms, "
          f"error_rate={health['error_rate']}%")

    # Step 3: 查询该服务的告警
    print(f"\n--- Step 3: 查询 '{target}' 的告警 ---")
    alerts = agent_call_cli(["alerts", "--service", target])
    print(f"[Agent] 发现 {len(alerts)} 条告警:")
    for alert in alerts:
        print(f"  [{alert['severity'].upper()}] {alert['message']}")

    # Step 4: Agent 做出诊断
    print(f"\n--- Step 4: Agent 综合诊断 ---")
    critical_alerts = [a for a in alerts if a["severity"] == "critical"]
    print(f"[Agent] 诊断结论: {target} 存在 {len(critical_alerts)} 个严重告警，"
          f"P99延迟 {health['latency_p99_ms']}ms 超出阈值，建议扩容。")


if __name__ == "__main__":
    agent_workflow()
