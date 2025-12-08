# **📘 Qwen-Agent 多 Agent 路由架构说明（带图例完整版）**

# **1. 设计目标与整体思路**

Qwen-Agent 路由层（Router）的核心目标是：

- 将多种能力（对话 / 图片 / 代码 / 文档 / 工作流）统一暴露为 **单一入口**
- 让 LLM 自动决策使用哪个 Agent
- 保证多轮对话中的 Agent identity 延续
- 保持低耦合、可扩展、可插拔

## **🔷 整体架构图**

```mermaid
flowchart TD
    User["用户输入"] --> MainRouter["MainChatRouter"]
    MainRouter --> QwenAgentRouter["QwenAgentRouter (LLM 路由器)"]

    QwenAgentRouter -->|命中启发式| PrevAgent["上一轮 Agent"]
    QwenAgentRouter -->|LLM 决策| RouteLLM["Call: <AgentName>"]

    RouteLLM --> AgentPool[["子 Agent 列表"]]

    AgentPool --> Basic["基础对话助手"]
    AgentPool --> Multi["多模态助手"]
    AgentPool --> Plan["规划助手"]
    AgentPool --> Code["代码助手"]
    AgentPool --> Docs["文档助手"]

    PrevAgent --> Output
    Basic --> Output["最终输出"]
    Multi --> Output
    Plan --> Output
    Code --> Output
    Docs --> Output
```

---

# **2. 核心组件说明**

## **2.1 QwenAgentRouter（路由器）**

路径：agents/core/routing/router.py

职责：

- 继承 FnCallAgent → 让 LLM 决策
- 继承 MultiAgentHub → 持有子 Agent 队列
- 强制输出格式 Call: <AgentName>
- 通过 stop=['\n'] 限定只读第一行

### **🔷 QwenAgentRouter 内部逻辑图**

```mermaid
flowchart TD
    A["接收上下文 + 最近消息"] --> B{"启发式命中？"}
    B -->|是| C["直接选择上轮 Agent"]
    B -->|否| D["给历史消息注入 Call: name"]
    D --> E["调用 LLM 输出 Call: <AgentName>"]
    E --> F{"解析成功？"}
    F -->|否| G["回退到兜底 Agent"]
    F -->|是| H["选择对应 Agent"]
    C --> I["进入子 Agent"]
    G --> I
    H --> I
```

---

## **2.2 子 Agent 类型**

| **Agent 名称**  | **文件**                            | **能力**     |
| ------------- | --------------------------------- | ---------- |
| **基础对话助手**    | agents/chat/basic_chat_agent.py   | 通用问答、兜底    |
| **多模态助手**     | agents/multimodal/image_agent.py  | 图像识别、图像生成  |
| **规划助手**      | agents/planning/planning_agent.py | 多步骤工作流拆解   |
| **代码助手**      | agents/code/code_agent.py         | 代码执行、调试、生成 |
| **文档助手（可扩展）** | 自定义                               | 文件阅读、检索、翻译 |

---

# **3. 消息流与路由流程（核心链路）**

---

## **🔷 路由行为时序图**

```mermaid
sequenceDiagram
    participant U as User
    participant M as MainChatRouter
    participant R as QwenAgentRouter
    participant L as 路由LLM
    participant SA as 子 Agent

    U->>M: ChatRequest
    M->>R: 准备上下文并进入路由器

    alt 启发式命中
        R->>R: select = 上一轮 Agent
    else 进入 LLM 决策
        R->>R: 注入 "Call: <name>"
        R->>L: "Call: ?"
        L-->>R: "Call: 多模态助手"
    end

    R->>SA: 转发用户消息
    SA-->>R: 返回回答 + Agent name
    R-->>U: 流式输出
```

---

# **4. 路由关键逻辑图例**

---

## **4.1 启发式判断流程**

```mermaid
flowchart LR
    A["用户最新问题"] --> B{"包含：继续 / 再来一个 / 这张图？"}
    B -->|是| C["直接沿用上一轮的 Agent"]
    B -->|否| D["进入 LLM 决策"]
```

---

## **4.2 历史消息注入 Call:**

## **（提示增强）**

```mermaid
flowchart LR
    A[遍历历史 assistant 消息] --> B{"有 text 段？"}
    B -->|是| C["在首个 text 段前插入：<br/>Call: <AgentName>"]
    B -->|否| D["保持原样（注意：业务需保证消息包含文本）"]
    C --> E["得到强化后的消息列表"]
    D --> E
```

---

## **4.3 LLM 决策 Agent**

```mermaid
flowchart TD
    A["LLM 输出文本"] --> B{"首行中含 Call: ?"}
    B -->|否| C["fallback=第一个 Agent（通常为基础对话助手）"]
    B -->|是| D["解析 <AgentName>"]
    D --> E{"AgentName 在列表中？"}
    E -->|否| C
    E -->|是| F["使用该 Agent"]
```

---

## **4.4 子 Agent 执行与响应回写**

```mermaid
flowchart TD
    A["Router 选择的 Agent"] --> B["去除 Router 的 system prompt"]
    B --> C["把用户原始消息转发给子 Agent"]
    C --> D["子 Agent 工作逻辑（FnCallAgent）"]
    D --> E["生成回答 + 工具调用"]
    E --> F["Router 回写 name 字段"]
```

---

# **5. 工具编排（call_sub_agent）**

call_sub_agent 将“调用另一个 Agent”抽象成工具调用，使规划 Agent 在同一轮内调用多个 Agent。

---

## **🔷 call_sub_agent 工作流图**

```mermaid
sequenceDiagram
    participant P as PlanningAgent
    participant Tool as call_sub_agent
    participant A as SubAgent

    P->>Tool: {"target": "ImageAgent", "instruction": "..."}
    Tool->>A: 构造新的消息上下文并执行
    A-->>Tool: 子 Agent 最终回答
    Tool-->>P: 返回最终内容
```

---

# **6. 底层设计原理（Why）**

---

## **6.1 为什么让 LLM 做路由？**

```mermaid
flowchart TD
    A["用户输入"] --> B["语义复杂、不可硬编码"]
    B --> C["LLM 可理解上下文语义"]
    C --> D["通过 prompt 控制路由策略"]
```

✔ 易维护

✔ 可扩展

✔ 修改 Prompt 即可调整策略

---

## **6.2 为什么要显式注入 “Call: name”**

```mermaid
flowchart TD
    A["多轮对话"] --> B["LLM 知道上一轮是谁？"]
    B --> C{"没有 Call: name?"}
    C -->|是| D["无法判断上下文延续 → 错选 Agent"]
    C -->|否| E["能正确接管上下文语境"]
```

---

## **6.3 为什么要启发式兜底？**

```mermaid
flowchart LR
    A["继续/再来/这张图"] --> B["无需语义路由"]
    B --> C["直接沿用上个 Agent"]
```

原因：

- 避免浪费模型调用
- 用户意图明确
- 保证多轮一致性

---

# **7. 扩展新 Agent 的完整接入流程（含示意图）**

---

## **7.1 步骤图**

```mermaid
flowchart LR
    A["实现新 Agent (FnCallAgent)"] --> B["在 main_chat_router 注册"]
    B --> C["加入 QwenAgentRouter 的 agents 列表"]
    C --> D["更新路由 Prompt（帮手列表 + 优先级）"]
    D --> E["完成接入"]
```

---

## **7.2 最小可用的新 Agent 模板**

```python
class BlogAgent(FnCallAgent):
    name = "博客助手"
    description = "负责博客理解与生成"

    def __init__(self):
        super().__init__(
            system_message="你是博客专家…",
            llm=qwen_llm,
            function_list=[blog_search, blog_summary]
        )
```

---

# **8. 已知局限与未来增强方向（图例增强版）**

---

## **8.1 当前局限图例**

```mermaid
flowchart TD
    A["路由不支持 FSM"] --> B["多轮延续可能误判"]
    C["复杂工作流未完全接入"] --> D["规划能力弱化"]
    E["LLM 输出无 schema"] --> F["解析失败风险"]
```

---

## **8.2 可增强方向**

- 引入意图分类器 + LLM 双路由策略
- 增加正则校验、自动重试
- 在消息 metadata 保存 agent_name
- 增加路由日志、统计、调优能力
- 将规划 Agent 全面接入路由列表

---

# **9. 关键文件总结**

```
agents/
  core/routing/router.py         # 路由器
  routers/main_chat_router.py    # 主入口
  chat/basic_chat_agent.py       # 基础对话助手
  multimodal/image_agent.py      # 多模态助手
  planning/planning_agent.py     # 工作流规划助手
  code/code_agent.py             # 代码助手
tools/
  orchestration/agent_call.py     # 子 Agent 调度工具
```
