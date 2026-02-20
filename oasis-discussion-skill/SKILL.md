---
name: oasis-discussion
description: >
  Orchestrate multi-agent discussions on the OASIS social simulation platform.
  Use this skill when users want to organize structured agent discussions, debates,
  brainstorming sessions, roundtable talks, or interviews. The skill generates
  YAML scheduling scripts and agent configurations, then launches the OASIS simulation.
  Keywords: OASIS, multi-agent, discussion, debate, brainstorm, roundtable, social simulation, agent schedule
---

# OASIS Discussion Orchestrator

## Purpose

Organize and run structured multi-agent discussions on the OASIS platform using YAML scheduling DSL. This skill turns a user's high-level intent ("组织一场 AI 伦理辩论") into a complete, runnable simulation.

## Base Directory

The OASIS project root (the directory containing `community_simulation.py`). All paths in this Skill are **relative to the project root**. The Skill itself lives at `oasis-discussion-skill/` under the project root.

Detect the project root at runtime:

```bash
OASIS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"  # if called from oasis-discussion-skill/scripts/
# Or simply: cd into the repo root before running commands
```

## When to Use

- User wants to set up a multi-agent discussion / debate / brainstorm / roundtable / interview
- User wants to control agent speaking order (serial / parallel / mixed)
- User wants to create custom discussion patterns on OASIS
- User mentions "OASIS 讨论" or "Agent 编排"

## Workflow

Follow these steps in order. At each step, reference the corresponding file under this skill directory.

### Step 1 — Clarify Discussion Intent

Ask or infer the following from the user:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `topic` | Discussion topic / initial post content | (required) |
| `pattern` | Discussion pattern: `debate` / `brainstorm` / `roundtable` / `interview` | `roundtable` |
| `num_agents` | Total number of agents (including external) | `6` |
| `rounds` | Number of simulation rounds | `3` |
| `external_agents` | Whether to include external agents (e.g. TimeBot) | `false` |
| `llm_platform` | LLM platform: `openai` / `deepseek` / `qwen` / `vllm` / `openai-compatible` | `openai-compatible` |
| `model_name` | Model identifier | (from env) |
| `api_url` | API endpoint | (from env) |
| `refresh_rec_post_count` | 每次 refresh 从推荐表采样的帖子数 | Twitter: `2`, Reddit: `5` |
| `max_rec_post_len` | 推荐表每用户最多缓存的帖子数 | Twitter: `2`, Reddit: `100` |
| `following_post_count` | 每次 refresh 从关注者获取的帖子数 | Twitter: `3` |

### Step 2 — Generate Agent Configuration

For **internal agents**, the system uses `build_agent_configs()` in `community_simulation.py` to auto-generate personas.

For **external agents** (e.g. TimeBot, custom bots), generate a JSON config file.

**Format** — see `references/agent_persona_library.md` for persona templates:

```json
[
    {
        "api_url": "http://127.0.0.1:51200/v1",
        "model": "mini-timebot",
        "api_key": "key",
        "platform_type": "openai-compatible",
        "temperature": 0.7,
        "name": "TimeBot",
        "user_name": "timebot",
        "description": "AI assistant with deep knowledge",
        "persona": "你是 TimeBot，一个博学多才的 AI 助手..."
    }
]
```

Use `scripts/generate_agents_config.py` to generate:

```bash
# 在项目根目录下运行
python oasis-discussion-skill/scripts/generate_agents_config.py \
  --roles "主持人,正方辩手,反方辩手,观察员" \
  --output external_agents.json
```

### Step 3 — Select or Generate Schedule YAML

Choose a template from `assets/templates/` based on the discussion pattern:

| Pattern | Template | Description |
|---------|----------|-------------|
| `debate` | `oasis-discussion-skill/assets/templates/debate.yaml` | Moderator + two sides + free debate + summary |
| `brainstorm` | `oasis-discussion-skill/assets/templates/brainstorm.yaml` | Parallel ideation → serial deepening → convergence |
| `roundtable` | `oasis-discussion-skill/assets/templates/roundtable.yaml` | Host-guided multi-round sequential discussion |
| `interview` | `oasis-discussion-skill/assets/templates/interview.yaml` | Interviewer asks, guests answer in turn |

Then customize the template based on user requirements. Reference `references/yaml_dsl_spec.md` for the complete YAML DSL syntax.

Use `scripts/generate_schedule.py` to generate from template:

```bash
# 在项目根目录下运行
python oasis-discussion-skill/scripts/generate_schedule.py \
  --pattern debate \
  --num-agents 6 \
  --rounds 3 \
  --output schedules/my_discussion.yaml
```

### Step 3.5 — Topic Injection via `manual` (推荐)

在 YAML 编排中使用 `manual` 指令让主持人/主控 Agent 直接发布话题帖，**比 `--initial-post` 更灵活**——可以按轮次设置不同话题，也可以让人类通过编辑 YAML 来精确控制讨论方向。

**基础用法** — 主持人发布话题后，其他 Agent 依次回应：

```yaml
vars:
  moderator: 0

plan:
  # 主持人发布话题
  - manual:
      agent: ${vars.moderator}
      action_type: create_post
      action_args:
        content: "今天的讨论话题：AI是否应该拥有自主决策权？请各位发表看法。"

  # 其他 Agent 依次回应（串行，后者能看到前者发言）
  - for_each:
      var: id
      in: "${range(1, num_agents)}"
    do:
      - llm:
          agent: ${id}
```

**按轮次设置不同话题** — 用 `if` 条件分支：

```yaml
plan:
  # 每轮由主持人发布不同话题
  - if:
      condition: "round == 1"
    then:
      - manual:
          agent: 0
          action_type: create_post
          action_args:
            content: "第一轮话题：AI的伦理边界在哪里？"
  - if:
      condition: "round == 2"
    then:
      - manual:
          agent: 0
          action_type: create_post
          action_args:
            content: "第二轮话题：如何监管AI的使用？"
  - if:
      condition: "round == 3"
    then:
      - manual:
          agent: 0
          action_type: create_post
          action_args:
            content: "第三轮话题：AI与人类的协作模式应该是什么？"

  # 每轮所有人回应
  - for_each:
      var: id
      in: "${range(1, num_agents)}"
    do:
      - llm:
          agent: ${id}
```

**与 `--initial-post` 的区别：**

| 方式 | 灵活度 | 多轮话题 | 适合场景 |
|------|--------|---------|---------|
| `manual` in YAML | 最高 | ✅ 每轮可不同 | 结构化讨论、辩论、精确控制 |
| `--initial-post` | 最简单 | ❌ 仅一条开场帖 | 快速测试 |
| `--topics-csv` | 批量自动 | ✅ 自动循环投放 | 大规模持续模拟 |

> **最佳实践**: 使用 `manual` 设置话题时，**必须**加 `--topics-num 0` 关闭 CSV 话题注入，可省略 `--initial-post` 参数或设为空字符串，避免无关话题干扰讨论焦点。

### Step 4 — Launch Simulation

```bash
# 在项目根目录下运行（cd 到 clone 下来的 oasis 目录）
python community_simulation.py \
  --num-agents <NUM> \
  --rounds <ROUNDS> \
  --schedule <PATH_TO_YAML> \
  --initial-post "<TOPIC>" \
  --llm-platform <PLATFORM> \
  --model-name <MODEL> \
  --api-url <URL> \
  --api-key <KEY> \
  --topics-num 0 \
  [--external-agents-config <JSON_PATH>] \
  [--temperature 0.7] \
  [--refresh-rec-post-count <N>] \
  [--max-rec-post-len <N>] \
  [--following-post-count <N>]
```

**Key CLI flags:**

| Flag | Required | Description |
|------|----------|-------------|
| `--schedule` | Yes (for this skill) | Path to the YAML schedule file |
| `--external-agents-config` | If using external agents | Path to external agent JSON |
| `--num-agents` | Yes | Must match the agent count in the YAML |
| `--rounds` | Yes | Number of discussion rounds |
| `--initial-post` | Recommended | The discussion topic / opening message |
| `--platform` | No | `twitter` (default) or `reddit` |
| `--topics-num` | **默认 `0`** | **关闭 CSV 无关话题注入**，避免干扰讨论焦点。如需额外话题可设为 >0 |
| `--refresh-rec-post-count` | No | 从推荐表采样帖子数 (Agent 少时建议调大, 如 5~10) |
| `--max-rec-post-len` | No | 推荐表每人缓存上限 (应 ≥ refresh 值) |
| `--following-post-count` | No | 关注者帖子数 (Agent 少时建议调大, 如 5~10) |

> **重要**: 默认使用 `--topics-num 0` 关闭 CSV 话题注入。OASIS 内置的 CSV 话题（新闻、热搜等）会严重干扰结构化讨论的焦点。话题应通过 YAML `manual` 指令或 `--initial-post` 来设置。

> **提示**: Agent 数量 ≤5 时，建议设置 `--refresh-rec-post-count 5 --max-rec-post-len 10 --following-post-count 10`，确保每个 Agent 能看到所有已有帖子。

### Step 5 — Monitor and Summarize

- **Logs**: Check `log/community-*.log` for real-time output
- **Database**: Query `community_simulation.db` with SQLite for posts and interactions
- **Viewer**: Use `community_viewer.py` for visualization (if available)

## YAML DSL Quick Reference

See `references/yaml_dsl_spec.md` for the full specification. Key instructions:

| Instruction | Purpose |
|-------------|---------|
| `llm` | Agent makes autonomous LLM-driven action (serial) |
| `parallel` | Multiple agents act concurrently |
| `manual` | Force a specific action (create_post, like, etc.) |
| `if/then/else` | Conditional branching |
| `for_each` | Iterate over a list |
| `repeat` | Fixed-count loop |
| `set` | Set a runtime variable |

## Important Notes

1. **Agent IDs**: Internal agents are 0-indexed. External agents are appended after internal ones.
   - If `num_agents=5` and 1 external agent, the external agent ID is `5`.
2. **`step_ordered` vs `step`**: When a schedule YAML is provided, the system uses `step_ordered()` (sequential with parallel groups), NOT `step()` (all-concurrent).
3. **Expression syntax**: Use `${expression}` in YAML values. Available context: `round`, `step`, `num_agents`, `vars`.
4. **Allowed builtins in expressions**: `range`, `len`, `min`, `max`, `int`, `float`, `bool`.

## Project File Structure (Skill-relevant only)

干净分支只保留 Skill 运行所需文件：

```
oasis/
├── community_simulation.py       # 主入口
├── dark_agent.py                 # PsySafe 黑暗人格模块（可选）
├── example_external_agent.py     # 外部 Agent HTTP 服务示例
├── external_agents_example.json  # 外部 Agent 配置示例
├── run_external_api.sh           # 一键启动脚本
├── pyproject.toml                # Python 依赖声明
├── .gitignore
├── LICENSE
├── oasis/                        # 核心 Python 包
│   ├── __init__.py
│   ├── clock/                    # 时钟控制
│   ├── environment/              # 环境 + ExternalAction
│   ├── scheduling/               # YAML DSL 编排引擎
│   ├── social_agent/             # Agent 图谱 + 行为
│   ├── social_platform/          # 平台 + 推荐系统 + DB schema
│   └── testing/                  # show_db 工具
├── oasis-discussion-skill/       # 本 Skill
│   ├── SKILL.md
│   ├── assets/templates/         # 讨论模式模板 YAML
│   ├── references/               # DSL 规范 + 模式参考
│   └── scripts/                  # 生成脚本
├── schedules/                    # 编排 YAML 文件
│   └── agent_schedule.example.yaml
├── community_viewer/             # 可视化前端（可选）
│   ├── index.html / app.js / styles.css
│   ├── export.py / live_server.py
│   └── data.json
└── data/                         # 话题数据（--topics-csv 需要，可选）
```

**已排除**：`docs/`、`examples/`(200+ 原始示例)、`generator/`、`visualization/`、`test/`、`.container/`、`.github/`、`assets/`(宣传素材)、`licenses/`、`deploy.py`、`download_model.sh`、`setup_env.sh` 等。
