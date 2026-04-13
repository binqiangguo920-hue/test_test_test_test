"""
Hermes Agent 入门示例
====================

什么是 Hermes Agent？
- 由 NousResearch 推出的开源 LLM 函数调用（Function Calling）协议
- 使用 XML 标签 <tool_call> / <tool_response> 让模型调用工具
- 支持 Hermes-2-Pro、Hermes-3 等开源模型
- 核心思想：ReAct 循环 —— 思考 → 调用工具 → 获取结果 → 继续思考

本示例不依赖任何外部 LLM，用一个"模拟 LLM"来演示完整的 Agent 循环流程，
让你理解 Hermes Agent 的工作原理。
"""

import json
import re

# ============================================================
# 第 1 步：定义工具（Tools）
# ============================================================
# Hermes 格式要求用 JSON Schema 描述每个工具的参数

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算数学表达式",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式，如 2+3*4"}
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "搜索知识库获取信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"]
            }
        }
    }
]


# ============================================================
# 第 2 步：实现工具的实际逻辑
# ============================================================

def get_weather(city: str) -> str:
    """模拟天气 API"""
    weather_db = {
        "北京": "晴天，28°C，湿度 45%",
        "上海": "多云，25°C，湿度 72%",
        "深圳": "雷阵雨，30°C，湿度 85%",
        "东京": "晴天，22°C，湿度 55%",
    }
    return weather_db.get(city, f"未找到 {city} 的天气数据")


def calculate(expression: str) -> str:
    """安全的数学计算"""
    allowed = set("0123456789+-*/.() ")
    if not all(c in allowed for c in expression):
        return "错误：表达式包含不允许的字符"
    try:
        result = eval(expression)  # 仅允许数学字符，已做安全过滤
        return str(result)
    except Exception as e:
        return f"计算错误：{e}"


def search_knowledge(query: str) -> str:
    """模拟知识库搜索"""
    kb = {
        "hermes": "Hermes 是 NousResearch 推出的开源 LLM 系列，支持函数调用和 Agent 能力。",
        "agent": "AI Agent 是能自主使用工具完成任务的智能体，核心是 ReAct 循环。",
        "react": "ReAct = Reasoning + Acting，让 LLM 交替进行思考和行动。",
    }
    for key, value in kb.items():
        if key in query.lower():
            return value
    return f"未找到与 '{query}' 相关的信息"


# 工具名 -> 函数的映射
TOOL_REGISTRY = {
    "get_weather": get_weather,
    "calculate": calculate,
    "search_knowledge": search_knowledge,
}


# ============================================================
# 第 3 步：构建 Hermes 格式的 System Prompt
# ============================================================

def build_system_prompt(tools: list) -> str:
    """
    Hermes 格式的核心：把工具定义放在 <tools> 标签里，
    并告诉模型用 <tool_call> 标签来调用工具。
    """
    tools_json = json.dumps(tools, ensure_ascii=False, indent=2)

    return f"""你是一个具有函数调用能力的 AI 助手。
你可以使用以下工具来帮助用户解决问题。工具定义在 <tools> 标签中：

<tools>
{tools_json}
</tools>

当你需要调用工具时，使用以下格式：
<tool_call>
{{"name": "工具名称", "arguments": {{"参数名": "参数值"}}}}
</tool_call>

你可以在调用工具前先思考，把思考过程写在普通文本中。
当你得到足够的信息后，直接用普通文本回答用户的问题。"""


# ============================================================
# 第 4 步：解析模型输出中的 <tool_call>
# ============================================================

def parse_tool_calls(text: str) -> list:
    """从模型输出中提取所有 <tool_call> 标签"""
    pattern = r"<tool_call>\s*(\{.*?\})\s*</tool_call>"
    matches = re.findall(pattern, text, re.DOTALL)
    calls = []
    for m in matches:
        try:
            calls.append(json.loads(m))
        except json.JSONDecodeError:
            print(f"  [解析错误] 无法解析: {m}")
    return calls


# ============================================================
# 第 5 步：执行工具调用
# ============================================================

def execute_tool(tool_call: dict) -> str:
    """根据解析出的工具调用，执行对应函数"""
    name = tool_call.get("name", "")
    args = tool_call.get("arguments", {})

    if name not in TOOL_REGISTRY:
        return f"错误：未知工具 '{name}'"

    func = TOOL_REGISTRY[name]
    return func(**args)


# ============================================================
# 第 6 步：模拟 LLM（演示用，实际中替换为真实模型调用）
# ============================================================

class MockHermesLLM:
    """
    模拟 Hermes 模型的行为。
    在实际项目中，这里会调用 vLLM / Ollama / HuggingFace 等推理服务。
    """

    def __init__(self):
        self.call_count = 0

    def generate(self, messages: list) -> str:
        """根据对话历史生成回复（模拟）"""
        self.call_count += 1
        user_msg = ""
        has_tool_response = False

        for msg in messages:
            if msg["role"] == "user":
                user_msg = msg["content"]
            if msg["role"] == "tool":
                has_tool_response = True

        # --- 模拟场景 1：查天气 ---
        if "天气" in user_msg and not has_tool_response:
            city = "北京"
            for c in ["北京", "上海", "深圳", "东京"]:
                if c in user_msg:
                    city = c
                    break
            return f"""让我查一下{city}的天气情况。
<tool_call>
{{"name": "get_weather", "arguments": {{"city": "{city}"}}}}
</tool_call>"""

        if "天气" in user_msg and has_tool_response:
            last_result = [m for m in messages if m["role"] == "tool"][-1]["content"]
            city = "北京"
            for c in ["北京", "上海", "深圳", "东京"]:
                if c in user_msg:
                    city = c
            return f"根据查询结果，{city}现在的天气是：{last_result}。建议你根据天气情况合理安排出行！"

        # --- 模拟场景 2：计算 ---
        if "计算" in user_msg or "算" in user_msg:
            expr_match = re.search(r"[\d\+\-\*\/\.\(\)\s]+", user_msg)
            expr = expr_match.group().strip() if expr_match else "1+1"
            if not has_tool_response:
                return f"""好的，我来帮你计算一下。
<tool_call>
{{"name": "calculate", "arguments": {{"expression": "{expr}"}}}}
</tool_call>"""
            else:
                last_result = [m for m in messages if m["role"] == "tool"][-1]["content"]
                return f"计算结果是：{expr} = {last_result}"

        # --- 模拟场景 3：搜索 ---
        if "什么是" in user_msg or "搜索" in user_msg:
            query = user_msg.replace("什么是", "").replace("搜索", "").replace("？", "").replace("?", "").strip()
            if not has_tool_response:
                return f"""让我搜索一下相关信息。
<tool_call>
{{"name": "search_knowledge", "arguments": {{"query": "{query}"}}}}
</tool_call>"""
            else:
                last_result = [m for m in messages if m["role"] == "tool"][-1]["content"]
                return f"根据搜索结果：{last_result}"

        # --- 默认：直接回答 ---
        return "你好！我是 Hermes Agent，我可以帮你查天气、做计算、搜索知识。请问有什么可以帮你的？"


# ============================================================
# 第 7 步：Agent 主循环 —— 这是核心！
# ============================================================

def run_agent(user_query: str, max_depth: int = 5):
    """
    Hermes Agent 的核心 ReAct 循环：

    用户提问
       ↓
    ┌─→ LLM 生成回复
    │      ↓
    │   包含 <tool_call>？ ─── 否 ──→ 输出最终回答，结束
    │      │ 是
    │      ↓
    │   解析并执行工具
    │      ↓
    │   将结果包装为 <tool_response> 放回对话
    └──────┘
    """
    print("=" * 60)
    print(f"  用户提问: {user_query}")
    print("=" * 60)

    llm = MockHermesLLM()

    # 构建初始对话
    messages = [
        {"role": "system", "content": build_system_prompt(TOOLS)},
        {"role": "user", "content": user_query},
    ]

    for depth in range(max_depth):
        print(f"\n--- 第 {depth + 1} 轮推理 ---")

        # 1. LLM 生成回复
        response = llm.generate(messages)
        print(f"  [LLM 输出]\n  {response}")

        # 2. 检查是否有工具调用
        tool_calls = parse_tool_calls(response)

        if not tool_calls:
            # 没有工具调用 → 这就是最终回答
            print(f"\n{'=' * 60}")
            print(f"  最终回答: {response}")
            print(f"{'=' * 60}")
            return response

        # 3. 执行工具调用
        messages.append({"role": "assistant", "content": response})

        for tc in tool_calls:
            print(f"\n  [调用工具] {tc['name']}({tc['arguments']})")
            result = execute_tool(tc)
            print(f"  [工具结果] {result}")

            # 4. 将结果包装为 <tool_response> 放回对话
            tool_response = f"<tool_response>\n{result}\n</tool_response>"
            messages.append({"role": "tool", "content": result})

    print("\n[警告] 达到最大循环深度，强制退出")
    return "抱歉，我无法在规定步数内完成任务。"


# ============================================================
# 第 8 步：运行演示！
# ============================================================

if __name__ == "__main__":
    print("\n" + "🤖 " * 20)
    print("    Hermes Agent 演示 —— 体验 AI Agent 的工作原理")
    print("🤖 " * 20)

    # 演示 1：查天气（工具调用）
    print("\n\n📌 演示 1：查询天气")
    run_agent("上海今天天气怎么样？")

    # 演示 2：数学计算（工具调用）
    print("\n\n📌 演示 2：数学计算")
    run_agent("帮我算一下 3.14 * 10 * 10")

    # 演示 3：知识搜索（工具调用）
    print("\n\n📌 演示 3：知识搜索")
    run_agent("什么是 Agent？")

    # 演示 4：普通对话（无需工具）
    print("\n\n📌 演示 4：普通对话（不需要工具）")
    run_agent("你好！")

    print("\n\n" + "=" * 60)
    print("演示结束！")
    print("""
📖 关键概念回顾：

1. <tools>      - 在 System Prompt 中定义可用工具（JSON Schema）
2. <tool_call>  - 模型输出此标签表示要调用某个工具
3. <tool_response> - 工具执行结果反馈给模型
4. ReAct 循环   - 思考 → 调用工具 → 获取结果 → 继续思考
5. 最大深度     - 防止无限循环的安全机制

🔧 要在实际项目中使用 Hermes Agent：
   - 将 MockHermesLLM 替换为真实模型（如通过 vLLM / Ollama 调用 Hermes-3）
   - 添加更多实用工具（HTTP 请求、数据库查询、文件操作等）
   - 参考：https://github.com/NousResearch/Hermes-Function-Calling
""")
