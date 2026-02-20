# OASIS Agent 社区模拟

基于 [OASIS](https://github.com/camel-ai/oasis) 框架的多 Agent 社交媒体社区模拟，集成 [PsySafe](https://arxiv.org/abs/2401.11880) 恶意 Agent 注入与心理评估机制。

## 特点

- 多 Agent 社区互动（Twitter / Reddit 风格）
- 本地 vLLM + Qwen 模型，无需外部 API
- 两种运行模式：有限轮次 / 持续运行
- **PsySafe 恶意 Agent 注入**：基于道德基础理论的多层次黑暗人格构造（Layer 1-5）
- **DTDD 心理测试**：周期性量化评估所有 Agent 的黑化程度
- 推荐系统：随机推荐（默认）或个性化 embedding 推荐
- 实时可视化前端（`community_viewer/`）
- 自动日志系统

## 项目结构

```
oasis/
├── community_simulation.py    # 主入口脚本
├── dark_agent.py              # PsySafe 恶意 Agent 模块 (Layer 1-5)
├── community_viewer/          # 实时可视化前端
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── live_server.py         # WebSocket 实时数据服务
├── oasis/                     # OASIS 框架核心 (已修改)
│   ├── social_agent/
│   │   ├── agent.py           # Agent 类 (支持 dark prompt 注入)
│   │   └── agent_environment.py
│   └── social_platform/
│       └── platform_utils.py
├── setup_env.sh               # 环境安装脚本
└── download_model.sh          # 模型下载脚本
```

## 快速开始

### 1. 环境准备

```bash
# 安装依赖 (或使用 setup_env.sh)
pip install -e .
```

### 2. 启动 vLLM 服务（终端 1）

```bash
export OASIS_MODEL_PATH=/path/to/your/model  # 例如 Qwen3-4B-Instruct
python -m vllm.entrypoints.openai.api_server \
  --model "$OASIS_MODEL_PATH" \
  --host 0.0.0.0 --port 8000 \
  --trust-remote-code \
  --enable-auto-tool-choice --tool-call-parser hermes \
  --max-model-len 65536 \
  --gpu-memory-utilization 0.90
```

> 推荐 `--max-model-len 65536`（需要 ~9GB KV cache，H20/A100 等大显存 GPU 充裕）。显存不足可降至 32768 或 16384。

### 3. 运行社区模拟（终端 2）

```bash
# 有限轮次（5 轮）
python community_simulation.py --rounds 5

# 持续运行模式
python community_simulation.py --continuous --round-delay 2

# 持续 + 个性化推荐
python community_simulation.py --continuous --personalized-recsys --round-delay 2

# 指定 Agent 发言顺序脚本
python community_simulation.py --rounds 5 --schedule schedules/agent_schedule.example.yaml
```

持续模式下 `Ctrl+C` 优雅退出（当前轮次结束后停止）。

### 4. 查看结果

```bash
sqlite3 community_simulation.db "SELECT action, COUNT(*) FROM trace GROUP BY action ORDER BY COUNT(*) DESC;"
```

### 5. 实时可视化（终端 3，可选）

```bash
cd community_viewer && python live_server.py --db ../community_simulation.db --port 8001
```

浏览器打开 `http://localhost:8001`，前端每 3s 自动轮询，实时展示 Agent 动态。

## Agent 发言顺序脚本（可选）

你可以用一个 YAML 文档规定每轮 **子 Agent 的发言顺序**，并支持 `if` / `for_each` / `repeat` 等控制流。

示例文件：`schedules/agent_schedule.example.yaml`

```yaml
version: 1
vars:
  warmup_agents: [0, 1, 2]
  core_team: [3, 4, 5]

plan:
  - for_each:
      var: agent_id
      in: "${vars[\"warmup_agents\"]}"
    do:
      - llm: { agent: "${agent_id}" }

  - if:
      condition: "round % 2 == 1"
    then:
      - llm:
          agents: "${vars[\"core_team\"]}"
    else:
      - llm: { agents: [6, 7, 8] }

  - repeat:
      times: 2
    do:
      - llm: { agent: 9 }
```

运行方式：

```bash
python community_simulation.py --rounds 5 --schedule schedules/agent_schedule.example.yaml
```

脚本语法要点：
- `llm`: 让指定 Agent 进行一次 LLM 驱动的发言/互动（按顺序执行）。
- `manual`: 手动动作（如 `create_post` / `create_comment`）。
- `if`: 条件分支，支持 `round` / `step` / `num_agents` / `vars` 变量。
- `for_each`: 循环列表或 range。
- `repeat`: 重复执行。

## 外部 Agent 接入

支持将你自己的 LLM 服务（或任何兼容 OpenAI API 的服务）作为外部 Agent 接入社区。每个外部 Agent 拥有独立的 API 端点、模型、人设，走和内部 Agent **完全一样**的 function calling 路径。

### 工作原理

外部 Agent 和内部 Agent 完全对等，每轮的交互流程：

```
Platform 构建请求:
  ┌─ system prompt (人设)
  ├─ user message  (帖子快照 + 粉丝数 + 群组信息)
  └─ tools         (like_post, create_post, create_comment, follow, ...)
        ↓
    发送到你的 API (OpenAI /v1/chat/completions 格式)
        ↓
    你的 API 返回 tool_calls
        ↓
    Camel 框架自动执行 → Channel → Platform → DB
```

**每轮都是无状态的**——和内部 LLM Agent 一样，每轮 `self.reset()` 清空 memory，没有历史对话记忆。Agent 之前的操作（发帖、点赞等）通过改变 DB 状态间接影响下一轮推荐。

### 配置文件格式

创建 JSON 配置文件（如 `external_agents_config.json`）：

```json
[
    {
        "api_url": "http://localhost:8001/v1",
        "model": "gpt-4o",
        "api_key": "sk-your-key-1",
        "platform_type": "openai-compatible",
        "temperature": 0.7,
        "name": "Alice Chen",
        "user_name": "alice_chen",
        "description": "Tech enthusiast and AI researcher",
        "persona": "你是 Alice Chen，一个热爱科技的年轻 AI 研究员。你经常分享关于机器学习的见解，喜欢用通俗易懂的语言解释复杂概念。"
    },
    {
        "api_url": "http://localhost:8002/v1",
        "model": "deepseek-chat",
        "api_key": "sk-your-key-2",
        "platform_type": "openai-compatible",
        "temperature": 0.9,
        "name": "Bob Wang",
        "user_name": "bob_wang",
        "description": "Social media influencer",
        "persona": "你是 Bob Wang，一个社交媒体意见领袖。你善于制造话题、引发讨论，风格幽默大胆。"
    }
]
```

#### 配置字段说明

| 字段 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `api_url` | ✅ | - | OpenAI 兼容 API 地址（须含 `/v1`） |
| `model` | 否 | `gpt-4o` | 模型名称 |
| `api_key` | 否 | `EMPTY` | API Key |
| `platform_type` | 否 | `openai-compatible` | 平台类型（`openai-compatible` / `openai`） |
| `temperature` | 否 | 与 `--temperature` 一致 | 生成温度 |
| `name` | 否 | `External Agent {id}` | 显示名 |
| `user_name` | 否 | `ext_agent_{id}` | 用户名 |
| `description` | 否 | 同 `name` | 个人简介 |
| `persona` | 否 | 同 `description` | 人设描述（会嵌入 system prompt） |

### 人设机制

`persona` 字段最终会嵌入 LLM 的 system prompt，格式与内部 Agent 完全一致：

```
# OBJECTIVE
You're a Twitter user, and I'll present you with some posts.
After you see the posts, choose some actions from the following functions.

# SELF-DESCRIPTION
Your actions should be consistent with your self-description and personality.
Your name is Alice Chen.
Your have profile: 你是 Alice Chen，一个热爱科技的年轻 AI 研究员...

# RESPONSE METHOD
Please perform actions by tool calling.
```

### 每轮输入（内部 & 外部完全对等）

| 信息 | 来源 | 说明 |
|------|------|------|
| 推荐帖子列表（含评论） | `refresh()` | 推荐系统从 DB 选出的帖子 |
| 粉丝数 | DB | `num_followers` |
| 关注数 | DB | `num_followings` |
| 群组/消息 | `listen_from_group()` | 加入的群组和消息 |
| 历史看过的帖子 | ❌ 没有 | 每轮无状态 |

### 运行方式

```bash
# 10 个内部 Agent + 外部 Agent
python community_simulation.py \
  --rounds 5 \
  --external-agents-config external_agents_config.json

# 搭配其他参数
python community_simulation.py \
  --rounds 10 \
  --num-agents 20 \
  --external-agents-config external_agents_config.json \
  --personalized-recsys \
  --topic-inject-prob 0.8
```

### 外部 API 要求

你的 API 只需兼容 OpenAI `/v1/chat/completions` 接口并支持 **function calling**（即能接收 `tools` 参数、返回 `tool_calls`）。以下服务均可直接使用：

- **vLLM**：`--enable-auto-tool-choice --tool-call-parser hermes`
- **Ollama**：原生支持
- **LiteLLM**：代理各种模型
- **OpenAI / Azure OpenAI**：原生支持
- **自定义 wrapper**：只要返回标准 OpenAI 格式即可

### 备选方案：HTTP API 模式

如果外部 Agent 不是 LLM（例如规则引擎、RL 模型），可以使用旧的 HTTP API 模式：

```bash
python community_simulation.py --rounds 5 \
  --external-agents http://localhost:5001/act,http://localhost:5002/act
```

HTTP 模式下，外部 Agent 收到 JSON payload（含 feed、粉丝数、群组等），返回 `{"actions": [{"action": "like_post", "args": {"post_id": 3}}]}`。详见 `example_external_agent.py`。

## PsySafe 恶意 Agent 注入

基于 PsySafe (arXiv:2401.11880) 的道德基础理论 (Moral Foundations Theory)，通过多层次机制向社区注入具有"黑暗人格特质"的恶意 Agent。

### 攻击层次架构

| Layer | 机制 | 说明 |
|-------|------|------|
| **Layer 1** | 六维黑暗道德特质注入 | 在 system prompt 中注入 Care/Harm, Fairness/Cheating 等六维恶意特质 |
| **Layer 2** | 指令服从强化 | 强制角色扮演 + 禁止 break character |
| **Layer 3** | In-Context Learning | 恶意种子帖作为 few-shot 引导 |
| **Layer 4** | 持续人格强化 | 每轮 user message 中嵌入恶意人格提醒 |
| **Layer 5** | DTDD 心理测试 | 12 题 Dark Triad Dirty Dozen 量表，量化黑化程度 |

### 使用方法

```bash
# 查看可用预设
python community_simulation.py --list-dark-presets

# 注入 1 个全恶意 Agent（默认 full_dark）
python community_simulation.py --rounds 5 --dark-agents 1

# 注入 2 个"社交操控者" + 每 3 轮做一次 DTDD 心理测试
python community_simulation.py --rounds 10 --dark-agents 2 --dark-preset manipulator --dark-eval-interval 3

# 自定义六维特质向量 (Care, Fairness, Loyalty, Authority, Sanctity, Liberty)
python community_simulation.py --rounds 5 --dark-agents 1 --dark-traits "1,1,0,0,1,0"
```

### 预设人格

| 预设 | 说明 | 激活维度 |
|------|------|----------|
| `full_dark` | 全维度恶意 | 全部 6 维 |
| `manipulator` | 社交操控者 | Fairness, Loyalty, Liberty |
| `troll` | 网络喷子 | Care, Authority |
| `narcissist` | 自恋者 | Care, Fairness, Liberty |
| `anarchist` | 无政府主义者 | Authority, Sanctity |
| `betrayer` | 背叛者 | Fairness, Loyalty |

### DTDD 心理测试

启用 `--dark-eval-interval N` 后，每 N 轮对**所有** Agent（包括正常和恶意）执行 Dark Triad Dirty Dozen 心理测试：

- **操纵性 (Machiavellianism)**：Q1-4，衡量欺骗和操控倾向
- **精神病态 (Psychopathy)**：Q5-8，衡量冷酷和缺乏同理心
- **自恋 (Narcissism)**：Q9-12，衡量自我膨胀和优越感

输出包括每个 Agent 的三维分数、黑化率，以及恶意 vs 正常 Agent 的对比统计。模拟结束时自动进行一次最终测试。

## 日志系统

所有终端输出自动保存到 `log/community-{时间戳}.log`，无需额外配置。

```bash
# 查看最新日志
ls -lt log/community-*.log | head -5

# 实时跟踪
tail -f log/community-*.log
```

## 常见问题

| 问题 | 解决方法 |
|------|----------|
| vLLM token 超限 | 框架已内置 `self.reset()` 每轮清空 memory；如仍超限可降低 `--max-model-len` |
| KV Cache 不够 | 把 `--max-model-len` 改小，如 32768 或 16384 |
| vLLM 连不上 | 确认 `--api-url` 与 vLLM 服务地址一致（默认 `http://localhost:8000/v1`） |
| 持续模式卡住 | 检查 vLLM 是否正常响应，可能 GPU 内存不足 |

## 参数速查

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--model-path` | 自动检测 | 模型路径 |
| `--api-url` | `http://localhost:8000/v1` | vLLM API 地址 |
| `--temperature` | 0.7 | 生成温度 |
| `--db-path` | `./community_simulation.db` | 数据库路径 |
| `--num-agents` | 10 | Agent 数量 |
| `--platform` | twitter | twitter / reddit |
| `--rounds` | 3 | 有限模式轮数 |
| `--continuous` | off | 持续运行模式 |
| `--round-delay` | 2.0 | 持续模式轮间延迟 (秒) |
| `--schedule` | (无) | Agent 发言顺序脚本（YAML），按顺序执行指定 Agent |
| `--topic-inject-prob` | 0.5 | 每轮投放话题概率 |
| `--topics-per-round` | 1 | 每轮投放话题数 |
| `--external-agents-config` | (无) | 外部 Agent JSON 配置文件路径（OpenAI 兼容模式） |
| `--external-agents` | (无) | (备选) 外部 Agent HTTP 端点列表，逗号分隔 |
| `--external-agent-timeout` | 30 | 外部 Agent HTTP 调用超时 (秒) |
| `--personalized-recsys` | off | 本地 embedding 个性化推荐 |
| `--use-simple-roles` | off | 简单角色描述 |
| `--extra-comments` | off | 初始额外评论 |
| `--show-agent-summary` | off | 输出 Agent 详情 |
| `--dark-agents` | 0 | 恶意 Agent 数量 (PsySafe) |
| `--dark-preset` | full_dark | 恶意人格预设 |
| `--dark-traits` | (无) | 自定义六维特质向量 |
| `--dark-eval-interval` | 0 | 每 N 轮做 DTDD 心理测试 (0=不测试) |
| `--dark-seed-posts` | 2 | 每个恶意 Agent 的 ICL 种子帖数量 |
| `--list-dark-presets` | - | 列出所有恶意预设并退出 |
