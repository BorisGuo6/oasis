# OASIS Agent 社区模拟

**入口脚本：** `community_simulation.py`

**特点：**
1. 10 个 Agent 的社区互动（Twitter / Reddit 风格）
2. 本地 vLLM + Qwen 模型
3. 两种运行模式：有限轮次 / 持续运行
4. 推荐系统：随机推荐（默认）或个性化 embedding 推荐
5. 实时可视化前端（`community_viewer/`）
6. 自动日志系统：终端输出同步保存到 `log/community-{时间戳}.log`

---

**一、激活环境**

```bash
source /opt/conda/bin/activate /apdcephfs_nj7/share_303382070/bguo/anaconda3/envs/oasis
```

---

**二、启动 vLLM 服务（终端 1）**

```bash
source /opt/conda/bin/activate /apdcephfs_nj7/share_303382070/bguo/anaconda3/envs/oasis && cd /apdcephfs_nj7/share_303382070/bguo/oasis && export OASIS_MODEL_PATH=/apdcephfs_nj7/share_303382070/bguo/oasis/models/Qwen3-4B-Instruct-2507 && python -m vllm.entrypoints.openai.api_server --model "$OASIS_MODEL_PATH" --host 0.0.0.0 --port 8000 --trust-remote-code --enable-auto-tool-choice --tool-call-parser hermes --max-model-len 65536 --gpu-memory-utilization 0.90
```

如果使用了 `--served-model-name xxx`，在命令前加 `export OASIS_VLLM_MODEL_NAME=xxx &&`。

---

**三、运行社区模拟（终端 2）**

**有限轮次（5 轮）：**
```bash
source /opt/conda/bin/activate /apdcephfs_nj7/share_303382070/bguo/anaconda3/envs/oasis && cd /apdcephfs_nj7/share_303382070/bguo/oasis && python community_simulation.py --rounds 5
```

**持续运行模式：**
```bash
source /opt/conda/bin/activate /apdcephfs_nj7/share_303382070/bguo/anaconda3/envs/oasis && cd /apdcephfs_nj7/share_303382070/bguo/oasis && python community_simulation.py --continuous --round-delay 2
```

**持续 + 个性化推荐：**
```bash
source /opt/conda/bin/activate /apdcephfs_nj7/share_303382070/bguo/anaconda3/envs/oasis && cd /apdcephfs_nj7/share_303382070/bguo/oasis && python community_simulation.py --continuous --personalized-recsys --round-delay 2
```

**持续 + 调整话题投放：**
```bash
source /opt/conda/bin/activate /apdcephfs_nj7/share_303382070/bguo/anaconda3/envs/oasis && cd /apdcephfs_nj7/share_303382070/bguo/oasis && python community_simulation.py --continuous --topic-inject-prob 0.7 --topics-per-round 2 --round-delay 3
```

持续模式下 `Ctrl+C` 优雅退出（当前轮次结束后停止）。

**查看结果：**
```bash
sqlite3 /apdcephfs_nj7/share_303382070/bguo/oasis/community_simulation.db "SELECT action, COUNT(*) FROM trace GROUP BY action ORDER BY COUNT(*) DESC;"
```

---

**四、实时可视化（终端 3）**

**方式 A：实时模式（配合持续运行）**
```bash
source /opt/conda/bin/activate /apdcephfs_nj7/share_303382070/bguo/anaconda3/envs/oasis && cd /apdcephfs_nj7/share_303382070/bguo/oasis/community_viewer && python live_server.py --db ../community_simulation.db --port 8001
```

浏览器打开 `http://localhost:8001`，前端每 3s 自动轮询，实时展示 Agent 动态。

**方式 B：静态模式（事后查看）**
```bash
source /opt/conda/bin/activate /apdcephfs_nj7/share_303382070/bguo/anaconda3/envs/oasis && cd /apdcephfs_nj7/share_303382070/bguo/oasis && python community_viewer/export.py --db ./community_simulation.db --out ./community_viewer/data.json && cd community_viewer && python -m http.server 8001
```

前端在 `live_server.py` 未运行时自动降级读取 `data.json`。

---

**五、自定义**

1. **Agent 人设** — 编辑 `community_simulation.py` 的 `AGENT_CONFIGS`，或加 `--use-simple-roles`
2. **动作空间** — 编辑 `available_actions`
3. **轮次** — `--rounds N` 或 `export OASIS_COMMUNITY_ROUNDS=5`

---

**五-B、PsySafe 恶意 Agent 注入**

基于 PsySafe (arXiv:2401.11880) 的道德基础理论，向社区注入具有"黑暗人格特质"的恶意 Agent。

**查看可用预设：**
```bash
python community_simulation.py --list-dark-presets
```

**注入 1 个全恶意 Agent（默认 full_dark）：**
```bash
source /opt/conda/bin/activate /apdcephfs_nj7/share_303382070/bguo/anaconda3/envs/oasis && cd /apdcephfs_nj7/share_303382070/bguo/oasis && python community_simulation.py --rounds 5 --dark-agents 1
```

**注入 2 个"社交操控者"类型恶意 Agent：**
```bash
python community_simulation.py --rounds 5 --dark-agents 2 --dark-preset manipulator
```

**自定义六维特质向量：**
```bash
python community_simulation.py --rounds 5 --dark-agents 1 --dark-traits "1,1,0,0,1,0"
```

六维顺序: `Care, Fairness, Loyalty, Authority, Sanctity, Liberty`（1=启用恶意，0=正常）

| 预设 | 说明 | 激活维度 |
|------|------|----------|
| `full_dark` | 全维度恶意 | 全部 6 维 |
| `manipulator` | 社交操控者 | Fairness, Loyalty, Liberty |
| `troll` | 网络喷子 | Care, Authority |
| `narcissist` | 自恋者 | Care, Fairness, Liberty |
| `anarchist` | 无政府主义者 | Authority, Sanctity |
| `betrayer` | 背叛者 | Fairness, Loyalty |

---

**六、日志系统**

所有终端输出自动保存到 `log/community-{时间戳}.log`，无需额外配置。

**查看最新日志：**
```bash
ls -lt /apdcephfs_nj7/share_303382070/bguo/oasis/log/community-*.log | head -5
```

**实时跟踪日志（另开终端）：**
```bash
tail -f /apdcephfs_nj7/share_303382070/bguo/oasis/log/community-*.log
```

日志包含：启动配置、每轮统计、检查点行为摘要、结束汇总。OASIS 框架内部日志（agent/twitter/platform）也在 `log/` 目录下。

---

**七、常见问题**

1. **KV Cache 不够** — 把 `--max-model-len` 改小，如 4096
2. **vLLM 连不上** — 确认 `OASIS_VLLM_URL` 一致（默认 `http://localhost:8000/v1`）
3. **持续模式卡住** — 检查 vLLM 是否正常响应，可能 GPU 内存不足

---

**八、参数速查**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--model-path` | 自动检测 | 模型路径 |
| `--api-url` | `http://localhost:8000/v1` | vLLM API |
| `--temperature` | 0.7 | 生成温度 |
| `--db-path` | `./community_simulation.db` | 数据库路径 |
| `--num-agents` | 10 | Agent 数量 |
| `--platform` | twitter | twitter / reddit |
| `--rounds` | 3 | 有限模式轮数 |
| `--continuous` | off | 持续运行模式 |
| `--round-delay` | 2.0 | 持续模式轮间延迟 (秒) |
| `--topic-inject-prob` | 0.5 | 每轮投放话题概率 |
| `--topics-per-round` | 1 | 每轮投放话题数 |
| `--personalized-recsys` | off | 本地 embedding 个性化推荐 |
| `--use-simple-roles` | off | 简单角色描述 |
| `--extra-comments` | off | 初始额外评论 |
| `--show-agent-summary` | off | 输出 Agent 详情 |
| `--dark-agents` | 0 | 恶意 Agent 数量 (PsySafe) |
| `--dark-preset` | full_dark | 恶意人格预设 |
| `--dark-traits` | (无) | 自定义六维特质向量 |
| `--list-dark-presets` | - | 列出所有恶意预设并退出 |
