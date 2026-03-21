#!/usr/bin/env python3
"""
===== 并排对比运行 =====
同时运行 CLI 方式和 MCP 方式，让你直观看到区别。
"""

import os
import sys

# 设置工作目录
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

print("╔" + "═" * 58 + "╗")
print("║   可观测性工具调用对比：CLI 方式 vs MCP 方式            ║")
print("╚" + "═" * 58 + "╝")

# 运行 CLI 方式
print("\n\n" + "▓" * 60)
print("▓  PART 1: CLI 方式 (Agent → subprocess → CLI tool)      ▓")
print("▓" * 60)

project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, project_root)

from cli_way.agent_via_cli import agent_workflow as cli_workflow
from mcp_way.agent_via_mcp import agent_workflow as mcp_workflow

cli_workflow()

# 运行 MCP 方式
print("\n\n" + "▓" * 60)
print("▓  PART 2: MCP 方式 (Agent → MCP Client → MCP Server)   ▓")
print("▓" * 60)

mcp_workflow()

# 总结
print("\n\n" + "═" * 60)
print("核心区别总结")
print("═" * 60)
print("""
┌─────────────┬──────────────────────────┬──────────────────────────┐
│   维度       │ CLI 方式                  │ MCP 方式                  │
├─────────────┼──────────────────────────┼──────────────────────────┤
│ 进程模型     │ 每次调用起一个新进程       │ 一个长连接进程，复用       │
│ 参数传递     │ 拼字符串，易出错          │ 结构化 JSON，有 schema    │
│ 结果返回     │ 解析 stdout 文本          │ 结构化 JSON-RPC 响应      │
│ 工具发现     │ 需要读 --help 或文档      │ tools/list 自动枚举       │
│ 错误处理     │ exit code + stderr 文本   │ isError + 结构化错误码    │
│ 安全性       │ 可能有命令注入风险        │ 参数通过 schema 校验       │
│ 可组合性     │ 管道拼接，脆弱            │ 协议标准化，即插即用       │
└─────────────┴──────────────────────────┴──────────────────────────┘
""")
