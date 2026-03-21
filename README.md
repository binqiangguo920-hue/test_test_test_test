# MCP vs CLI：Agent 调用可观测性工具的对比演示

## 场景

一个 AI Agent 需要**诊断微服务故障**，工作流如下：
1. 列出所有服务 → 2. 发现异常服务 → 3. 查健康状态 → 4. 查告警 → 5. 给出诊断

同一个工作流，分别用 **CLI 方式** 和 **MCP 方式** 实现，对比 Agent 调用功能的区别。

## 项目结构

```
.
├── backend/                    # 共享的可观测性后端（模拟数据）
│   └── observability_service.py
├── cli_way/                    # CLI 方式
│   ├── obs_cli.py              # 命令行工具（argparse）
│   └── agent_via_cli.py        # Agent 通过 subprocess 调用 CLI
├── mcp_way/                    # MCP 方式
│   ├── obs_mcp_server.py       # MCP Server（JSON-RPC over stdio）
│   └── agent_via_mcp.py        # Agent 通过 MCP Client 调用工具
└── agent_demo/
    └── run_comparison.py       # 并排对比运行
```

## 快速运行

```bash
python3 agent_demo/run_comparison.py
```

## 核心区别详解

### 1. 工具发现

**CLI**: Agent 必须预先知道命令行用法，或解析 `--help` 的非结构化文本。
```python
# Agent 需要"硬编码"知道有哪些子命令
agent_call_cli(["health", "order-service"])
agent_call_cli(["alerts", "--service", "order-service"])
```

**MCP**: Agent 调用 `tools/list` 自动获得工具列表 + JSON Schema。
```python
tools = client.list_tools()
# 返回: [{"name": "get_service_health", "inputSchema": {...}}, ...]
# Agent 自动知道每个工具接受什么参数、什么类型
```

### 2. 参数传递

**CLI**: 拼字符串数组，容易出现转义、空格、引号问题。
```python
# 如果服务名包含空格或特殊字符就会出错
subprocess.run(["python3", "obs_cli.py", "health", service_name])
```

**MCP**: 传 JSON 对象，有 schema 校验。
```python
client.call_tool("get_service_health", {"service_name": service_name})
```

### 3. 进程模型

**CLI**: 每次调用 fork 一个新进程，有启动开销，无法共享状态。
```
调用1: fork → exec → 输出 → exit
调用2: fork → exec → 输出 → exit  （完全独立）
调用3: fork → exec → 输出 → exit
```

**MCP**: 一个长连接进程，所有调用复用。
```
启动:   fork MCP Server
调用1:  stdin → JSON-RPC → stdout  ─┐
调用2:  stdin → JSON-RPC → stdout   ├─ 同一个进程
调用3:  stdin → JSON-RPC → stdout  ─┘
```

### 4. 错误处理

**CLI**: exit code + stderr 文本，Agent 只能猜测错误原因。
```python
if result.returncode != 0:
    # stderr 可能是: "Error: service not found" 也可能是 Python traceback
    # Agent 很难程序化区分
```

**MCP**: 结构化错误，有错误码和消息。
```json
{"isError": true, "content": [{"type": "text", "text": "Service 'xxx' not found"}]}
```

### 5. 安全性

**CLI**: 参数拼接存在命令注入风险。
```python
# 如果 service_name = "; rm -rf /" 就危险了
os.system(f"obs_cli.py health {service_name}")
```

**MCP**: 参数通过 JSON 传递 + schema 校验，天然防注入。

## 一句话总结

> **CLI 是给人用的，MCP 是给 Agent 用的。**
>
> CLI 的设计哲学是"文本即接口"，适合人类在终端交互；
> MCP 的设计哲学是"结构化协议即接口"，适合 AI Agent 程序化调用。
