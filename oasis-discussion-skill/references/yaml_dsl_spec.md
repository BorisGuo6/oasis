# OASIS YAML Schedule DSL — Complete Specification

## File Structure

```yaml
version: 1          # Optional, for future compatibility
vars:                # Optional: define reusable variables
  key: value
plan:                # Required: list of instructions
  - instruction1
  - instruction2
```

## Expression System

### Template Syntax

Use `${expression}` anywhere in values. Examples:

```yaml
agent: "${vars[\"moderator\"]}"
agents: "${range(num_agents)}"
condition: "round % 2 == 0"
value: "${round * 2 + 1}"
```

### Available Context Variables

| Variable | Type | Description |
|----------|------|-------------|
| `round` | int | Current round number (0-indexed) |
| `step` | int | Current step number within the round |
| `num_agents` | int | Total number of agents in the environment |
| `vars` | dict | User-defined variables from `vars:` section and `set` instructions |

### Allowed Built-in Functions

`range`, `len`, `min`, `max`, `int`, `float`, `bool`

### Safety

Expressions are evaluated via AST whitelist. The following are **forbidden**:
- Attribute access (`obj.attr`) — use `vars["key"]` instead
- Imports, function definitions, class definitions
- Any non-whitelisted AST node types

---

## Agent ID Resolution

All instructions that target agents support 4 ways to specify them:

### 1. Single Agent — `agent`

```yaml
- llm: { agent: 0 }
- llm: { agent: "${vars[\"moderator\"]}" }
```

### 2. Agent List — `agents`

```yaml
- llm: { agents: [1, 2, 3] }
- llm: { agents: "${vars[\"core_team\"]}" }
```

### 3. Range — `range`

```yaml
# Inclusive range: agents 0 through 9
- llm: { range: [0, 9] }

# With step
- llm: { range: { start: 0, end: 9, step: 2 } }
```

**Note**: Range end is **inclusive** (unlike Python's range).

### 4. Named Group — `group`

```yaml
vars:
  debate_team: [3, 4, 5]

plan:
  - llm: { group: debate_team }
```

Looks up the group name in `vars`.

---

## Instructions Reference

### 1. `llm` (alias: `speak`)

Make agent(s) perform an autonomous LLM-driven action. The agent decides what to do (post, comment, like, etc.) based on its context.

**Serial execution**: agents act one by one in order.

```yaml
# Single agent
- llm: { agent: 0 }

# Multiple agents (serial)
- llm: { agents: [1, 2, 3] }

# Range
- llm: { range: [0, 4] }

# Named group
- llm: { group: core_team }
```

### 2. `parallel`

Make multiple agents act **concurrently** via `asyncio.gather`.

```yaml
- parallel: { agents: [1, 2, 3] }
- parallel: { range: [0, 9] }
- parallel: { group: brainstorm_team }
```

**Difference from `llm`**: `llm` with multiple agents runs them serially; `parallel` runs them concurrently. Use `parallel` when agents don't need to see each other's output within the same step.

### 3. `manual`

Force a specific predefined action.

```yaml
- manual:
    agent: 0
    action_type: create_post
    action_args:
      content: "This is a forced post from the schedule."

# Supported action_types (from ActionType enum):
# create_post, repost, like_post, unlike_post,
# follow_user, unfollow_user, mute_user, unmute_user,
# create_comment, like_comment, unlike_comment,
# do_nothing, interview
```

### 4. `if` / `then` / `else`

Conditional branching based on expression evaluation.

```yaml
- if:
    condition: "round % 2 == 1"
  then:
    - llm: { agents: [3, 4, 5] }
  else:
    - llm: { agents: [6, 7, 8] }
```

- `condition`: Expression string evaluated to boolean
- `then`: Executed if condition is truthy (optional)
- `else`: Executed if condition is falsy (optional)

### 5. `for_each`

Iterate over a list or range.

```yaml
# Iterate over a list
- for_each:
    var: agent_id
    in: "${vars[\"warmup_agents\"]}"
  do:
    - llm: { agent: "${agent_id}" }

# Iterate over a range
- for_each:
    var: i
    in: { range: [0, 4] }
  do:
    - llm: { agent: "${i}" }

# Default loop variable is "item"
- for_each:
    in: [1, 2, 3]
  do:
    - llm: { agent: "${item}" }
```

- `var`: Loop variable name (default: `item`)
- `in`: Iterable — list, expression string, or `{ range: [start, end] }`
- `do`: Loop body (list of instructions)

### 6. `repeat`

Execute a block a fixed number of times.

```yaml
- repeat:
    times: 3
  do:
    - llm: { agent: 0 }
    - parallel: { agents: [1, 2, 3] }
```

### 7. `set`

Set a runtime variable.

```yaml
- set:
    var: current_speaker
    value: "${round % num_agents}"
```

The variable is immediately available in subsequent expressions via `vars["current_speaker"]` or directly as `current_speaker`.

---

## YAML Syntax Styles

Both compact and expanded styles are supported:

### Compact (inline)

```yaml
- for_each: { var: x, in: [1, 2, 3], do: [{ llm: { agent: "${x}" } }] }
```

### Expanded (recommended)

```yaml
- for_each:
    var: x
    in: [1, 2, 3]
  do:
    - llm: { agent: "${x}" }
```

The same applies to `if/then/else`, `repeat/do`, and `parallel`.

---

## Complete Example

```yaml
version: 1
vars:
  warmup_agents: [0, 1, 2]
  core_team: [3, 4, 5]

plan:
  # Serial warm-up
  - for_each:
      var: agent_id
      in: "${vars[\"warmup_agents\"]}"
    do:
      - llm: { agent: "${agent_id}" }

  # Conditional branching by round
  - if:
      condition: "round % 2 == 1"
    then:
      - llm: { agents: "${vars[\"core_team\"]}" }
    else:
      - llm: { agents: [6, 7, 8] }

  # Repeat block
  - repeat:
      times: 2
    do:
      - llm: { agent: 9 }

  # Parallel execution
  - parallel: { agents: [1, 2, 3] }

  # Manual action
  - manual:
      agent: 0
      action_type: create_post
      action_args:
        content: "Scripted post from schedule."
```
