# Discussion Patterns Reference

Pre-built discussion patterns for common multi-agent interaction scenarios. Each pattern has a corresponding YAML template in `assets/templates/`.

---

## 1. Debate (辩论)

**File**: `assets/templates/debate.yaml`

**Structure**:
- 1 Moderator (主持人) — Agent 0
- N agents on Side A (正方)
- N agents on Side B (反方)
- 1 Observer/Summarizer (观察员) — last agent

**Flow**:
```
Round:
  1. Moderator opens / guides (manual: create_post with topic)
  2. Side A presents arguments (parallel)
  3. Side B rebuts (parallel)
  4. Free debate: alternating serial exchanges
  5. Observer summarizes
```

**Best for**: Controversial topics, policy discussions, pros/cons analysis.

**Agent count recommendation**: 5–8 (1 mod + 2–3 per side + 1 observer)

---

## 2. Brainstorm (头脑风暴)

**File**: `assets/templates/brainstorm.yaml`

**Structure**:
- All agents are equal participants
- No fixed moderator (or optional facilitator as Agent 0)

**Flow**:
```
Round:
  1. All agents throw out ideas (parallel — fast, independent)
  2. Each agent deepens/builds on ideas (serial — can see previous)
  3. All respond to the collective pool (parallel)
```

**Best for**: Creative ideation, feature brainstorming, solution exploration.

**Agent count recommendation**: 4–8

---

## 3. Roundtable (圆桌讨论)

**File**: `assets/templates/roundtable.yaml`

**Structure**:
- 1 Host (主持人) — Agent 0
- N Panelists (嘉宾)

**Flow**:
```
Round:
  1. Host introduces topic / asks question (manual: create_post with topic)
  2. Each panelist speaks in turn (serial for_each)
  3. Host summarizes the round
  Repeat for multiple rounds
```

**Best for**: Structured discussions, expert panels, topic deep-dives.

**Agent count recommendation**: 4–7 (1 host + 3–6 panelists)

---

## 4. Interview (访谈)

**File**: `assets/templates/interview.yaml`

**Structure**:
- 1 Interviewer (采访者) — Agent 0
- 1–3 Interviewees (被采访者)
- Optional audience agents

**Flow**:
```
Round:
  1. Interviewer asks a question (manual: create_post with question)
  2. Interviewee(s) respond (serial)
  3. Follow-up exchange
  4. Audience reacts (parallel, optional)
```

**Best for**: Expert interviews, Q&A sessions, knowledge extraction.

**Agent count recommendation**: 2–5 (1 interviewer + 1–2 guests + optional audience)

---

## 5. Custom Pattern Design Guide

When none of the pre-built patterns fit, design a custom one:

### Key Decisions

1. **Who speaks first?** — Usually a moderator or topic-setter
2. **Serial vs Parallel?**
   - Serial: when later speakers should see earlier content
   - Parallel: when independent, simultaneous responses are desired
3. **How many rounds?** — More rounds = deeper discussion
4. **Conditional logic?** — Use `if` for dynamic flow (e.g., odd/even rounds differ)
5. **Variables?** — Use `vars` and `set` for agent grouping and dynamic state

### Common Patterns

```yaml
# Pattern: Moderator-guided with rotating spotlight
- llm: { agent: 0 }                    # Moderator
- llm: { agent: "${round % (num_agents - 1) + 1}" }  # Rotating speaker
- parallel: { range: [1, "${num_agents - 1}"] }       # All react

# Pattern: Progressive disclosure
- llm: { agent: 0 }                    # Seed idea
- repeat:
    times: "${num_agents - 1}"
  do:
    - llm: { agent: "${step}" }         # Each adds to the thread

# Pattern: Debate with vote
- parallel: { agents: "${vars[\"side_a\"]}" }
- parallel: { agents: "${vars[\"side_b\"]}" }
- parallel: { range: [0, "${num_agents - 1}"] }  # Everyone "votes" by reacting
```
