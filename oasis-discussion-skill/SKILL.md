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
  [--external-agents-config <JSON_PATH>] \
  [--temperature 0.7]
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
