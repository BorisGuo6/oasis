# Oasis Agent 社区搭建指南

基于 oasis 框架搭建的 10 Agent 社区，使用本地 Qwen3-4B-Instruct-2507 模型

## 📋 目录
- [环境准备](#环境准备)
- [快速开始](#快速开始)
- [代码结构](#代码结构)
- [运行说明](#运行说明)
- [自定义配置](#自定义配置)
- [常见问题](#常见问题)

## 🛠 环境准备

### 1. 安装依赖

```bash
# 安装 oasis
cd oasis
pip install -e .

# 安装 vLLM（用于本地模型推理）
pip install vllm

# 确保安装其他依赖
pip install camel-ai pandas
```

### 2. 准备模型

确保模型文件存在于：
```
models/Qwen3-4B-Instruct-2507
```

### 3. 启动 vLLM 服务器

```bash
# 在一个单独的终端中运行
python -m vllm.entrypoints.openai.api_server \
  --model models/Qwen3-4B-Instruct-2507 \
  --host 0.0.0.0 \
  --port 8000 \
  --trust-remote-code \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

## 🚀 快速开始

### 运行社区模拟

```bash
cd oasis
python community_sim_0131_0204.py
```

## 📁 代码结构

### 核心文件

```
oasis/
├── community_simulation.py    # 主要的模拟代码
├── my_oasis_community.py      # 完整版本（包含更多功能）
└── README_MY_COMMUNITY.md     # 本文档
```

### 主要组件

1. **Agent 配置** (`AGENT_CONFIGS`)
   - 10 个不同背景的 AI Agent
   - 每个 Agent 有独特的用户名、名称、描述和个人特质

2. **模型配置**
   - 使用 vLLM 部署本地 Qwen3-4B-Instruct-2507 模型
   - API 地址：`http://localhost:8000/v1`

3. **社交动作**
   - 点赞/取消点赞帖子
   - 发布帖子和评论
   - 关注/取消关注其他 Agent

## 💻 代码详解

### 1. 创建模型实例

```python
from camel.models import ModelFactory, ModelManager
from camel.types import ModelPlatformType

model = await create_qwen_model(
    model_path="models/Qwen3-4B-Instruct-2507",
    api_url="http://localhost:8000/v1"
)

model_manager = ModelManager(
    models=[model],
    scheduling_strategy='round_robin'
)
```

### 2. 创建 Agent

```python
from oasis import SocialAgent, UserInfo, AgentGraph

user_info = UserInfo(
    user_name="tech_explorer",
    name="Alice",
    description="科技爱好者",
    profile={"other_info": {"user_persona": "对AI充满热情"}},
    recsys_type="twitter",
)

agent = SocialAgent(
    agent_id=0,
    user_info=user_info,
    agent_graph=agent_graph,
    model=model_manager,
    available_actions=available_actions,
)

agent_graph.add_agent(agent)
```

### 3. 设置社交网络

```python
# 建立关注关系
for i in range(10):
    for j in range(10):
        if i != j and j % 2 == 0:  # 每个 Agent 关注一半的其他 Agent
            agent_graph.add_edge(i, j)
```

### 4. 运行模拟

```python
import oasis

# 创建环境
env = oasis.make(
    agent_graph=agent_graph,
    platform=oasis.DefaultPlatformType.TWITTER,
    database_path="./community_simulation.db"
)

# 初始帖子
await env.step({
    env.agent_graph.get_agent(0): [
        ManualAction(
            action_type=ActionType.CREATE_POST,
            action_args={"content": "欢迎来到 Agent 社区！"}
        )
    ]
})

# Agent 自主交互
actions = {agent: LLMAction() for _, agent in env.agent_graph.get_agents()}
await env.step(actions)
```

## ⚙️ 自定义配置

### 修改 Agent 数量

```python
# 在 AGENT_CONFIGS 中添加或移除配置
AGENT_CONFIGS = [
    # 添加新的 Agent
    {"agent_id": 10, "user_name": "new_agent", "name": "New Agent", 
     "description": "新 Agent", "persona": "个人特质"},
]
```

### 更换模型

```python
# 使用不同的本地模型
model = await create_qwen_model(
    model_path="/path/to/your/model",
    api_url="http://localhost:8000/v1"
)
```

### 修改社交动作

```python
available_actions = [
    ActionType.LIKE_POST,
    ActionType.CREATE_POST,
    ActionType.CREATE_COMMENT,
    ActionType.FOLLOW,
    # 添加更多动作...
]
```

## ❓ 常见问题

### Q1: vLLM 服务器无法启动？

**解决方案**：
1. 检查模型路径是否正确
2. 确保有足够的 GPU 内存
3. 检查端口 8000 是否被占用
4. 添加 `--trust-remote-code` 参数（Qwen 模型必需）

### Q2: 模型加载失败？

**解决方案**：
1. 确认 vLLM 服务器正在运行
2. 检查 API 地址是否正确
3. 验证模型文件完整性

### Q3: 如何查看交互结果？

**解决方案**：
1. 查看控制台输出
2. 检查生成的数据库文件：`community_simulation.db`
3. 查看日志文件：`./log/` 目录

### Q4: 如何增加交互轮次？

**修改代码**：
```python
for round_num in range(10):  # 改为 10 轮
    actions = {agent: LLMAction() for _, agent in env.agent_graph.get_agents()}
    await env.step(actions)
```

## 📊 输出示例

运行成功后会看到：

```
🚀 启动 Oasis Agent 社区...
📦 加载模型: models/Qwen3-4B-Instruct-2507
✅ 模型加载成功
👥 创建 10 个 Agents...
  - Agent 0: Alice
  - Agent 1: Bob
  ...
🔗 建立社交网络...
✅ 社交网络构建完成
🌐 创建模拟环境...
✅ 环境准备就绪
📝 发布初始内容...
🤖 开始 Agent 交互...
  轮次 1/3
  轮次 2/3
  轮次 3/3

📊 社区统计:
========================================
Agent 0: Alice (@tech_explorer)
Agent 1: Bob (@data_scientist)
...

✅ 模拟完成！数据库: community_simulation.db
```

## 🔧 进阶功能

### 1. 数据分析

```python
# 查看数据库内容
from oasis.testing import print_db_contents
print_db_contents("./community_simulation.db")
```

### 2. 自定义 Agent 行为

```python
# 手动控制 Agent 行为
await env.step({
    env.agent_graph.get_agent(0): [
        ManualAction(
            action_type=ActionType.CREATE_POST,
            action_args={"content": "自定义内容"}
        )
    ]
})
```

### 3. 混合使用 LLM 和手动控制

```python
# 部分 Agent 手动控制，部分使用 LLM
actions = {}
for agent_id, agent in env.agent_graph.get_agents():
    if agent_id == 0:  # Agent 0 手动控制
        actions[agent] = ManualAction(
            action_type=ActionType.CREATE_POST,
            action_args={"content": "手动发布的内容"}
        )
    else:  # 其他 Agent 使用 LLM
        actions[agent] = LLMAction()

await env.step(actions)
```

## 📝 注意事项

1. **资源要求**：确保有足够的 GPU 内存运行模型
2. **服务器稳定性**：保持 vLLM 服务器运行
3. **数据库管理**：每次运行会创建新的数据库文件
4. **日志查看**：定期清理 `./log/` 目录中的日志文件

## 📄 许可证

本项目基于 Apache License 2.0 许可证。
