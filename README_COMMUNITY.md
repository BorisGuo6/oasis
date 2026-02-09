# OASIS 单一 Agent 社区模拟（合并版）

本说明合并自 `README.md`、`README_MY_COMMUNITY.md` 和 `README_OASIS_COMMUNITY_0204_1334.md`，只保留**一个社区模拟**的最小可运行流程。

**你要跑的入口脚本：** `community_simulation.py`

**脚本特点：**
1. 10 个 Agent 的社区互动（Twitter 风格）。
2. 本地 vLLM + Qwen3-4B-Instruct-2507 模型。
3. 已打补丁：推荐系统使用随机推荐，避免下载 HuggingFace 依赖。

---

**一、环境准备**

1. 进入项目并安装依赖
```bash
cd /home/boris/workspace/oasis
pip install -e .
pip install vllm camel-ai pandas
```

2. 下载模型到本地（已下载可跳过）
```bash
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="Qwen/Qwen3-4B-Instruct-2507",
    local_dir="/home/boris/workspace/oasis/models/Qwen3-4B-Instruct-2507",
    resume_download=True
)
PY
```

---

**二、启动 vLLM 服务（单独终端）**

```bash
export OASIS_MODEL_PATH=/home/boris/workspace/oasis/models/Qwen3-4B-Instruct-2507

python -m vllm.entrypoints.openai.api_server \
  --model "$OASIS_MODEL_PATH" \
  --host 0.0.0.0 \
  --port 8000 \
  --trust-remote-code \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90
```

如果你启动 vLLM 时使用了 `--served-model-name xxx`，请额外设置：
```bash
export OASIS_VLLM_MODEL_NAME=xxx
```

---

**三、运行社区模拟**

```bash
cd /home/boris/workspace/oasis
python community_simulation.py --rounds 3 --db-path ./community_simulation.db
```

常用参数示例：
```bash
# Reddit 平台 + 简单角色描述
python community_simulation.py --platform reddit --use-simple-roles

# 指定 Agent 数量和轮次
python community_simulation.py --num-agents 20 --rounds 5

# 额外评论 + 输出 Agent 详情
python community_simulation.py --extra-comments --show-agent-summary
```

结果数据库：`/home/boris/workspace/oasis/community_simulation.db`

快速查看结果：
```bash
sqlite3 /home/boris/workspace/oasis/community_simulation.db \
  "SELECT action, COUNT(*) FROM trace GROUP BY action ORDER BY COUNT(*) DESC;"
```

---

**四、自定义最小改动**

1. Agent 人设  
编辑 `community_simulation.py` 里的 `AGENT_CONFIGS`，或运行时用：
```bash
python community_simulation.py --use-simple-roles
```

2. 动作空间  
编辑 `community_simulation.py` 里的 `available_actions`。

3. 轮次  
命令行加 `--rounds N`，或设置环境变量：
```bash
export OASIS_COMMUNITY_ROUNDS=5
```

4. 其他常用参数  
```bash
python community_simulation.py --platform twitter --num-agents 10 --extra-comments --show-agent-summary
```

---

**五、常见问题**

1. **KV Cache 不够**  
报错 `KV cache is needed...` 时，把 `--max-model-len` 改小，例如 4096。

2. **Agent 报 'like_comment' 错误**  
是动作不在 `available_actions` 里。把下面这行加入：
```python
ActionType.LIKE_COMMENT,
```

3. **vLLM 启动但社区脚本连不上**  
确认 `OASIS_VLLM_URL` 一致（默认是 `http://localhost:8000/v1`）。

---

**环境变量速查**

```
OASIS_MODEL_PATH=/home/boris/workspace/oasis/models/Qwen3-4B-Instruct-2507
OASIS_VLLM_MODEL_NAME=xxx                    # 可选，仅在 --served-model-name 时需要
OASIS_VLLM_URL=http://localhost:8000/v1
OASIS_DB_PATH=./community_simulation.db
OASIS_COMMUNITY_ROUNDS=3
OASIS_NUM_AGENTS=10
OASIS_PLATFORM=twitter
OASIS_RECSYS_TYPE=twitter
OASIS_SIMPLE_ROLES=0
OASIS_MODEL_TEMPERATURE=0.7
OASIS_INITIAL_POST=...
OASIS_EXTRA_COMMENTS=0
OASIS_SHOW_AGENT_SUMMARY=0
```
