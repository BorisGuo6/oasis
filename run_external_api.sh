#!/bin/bash
set -e

# ============================================================
#  OASIS 社区模拟 — 外部 LLM API 一键启动脚本
#
#  用法:
#    1. 编辑下方配置区，填入你的 API Key 和模型信息
#    2. bash run_external_api.sh
#
#  依赖管理: uv (自动安装 uv + 创建 venv + 安装依赖)
#  支持平台: openai / deepseek / qwen / openai-compatible
# ============================================================

# ── 代理（内网环境需要，外网可注释掉） ──
# 当前机器可直连外网，不需要代理；如在内网环境取消下面注释
# export http_proxy="http://star-proxy.oa.com:3128"
# export https_proxy="http://star-proxy.oa.com:3128"
# export HTTP_PROXY="$http_proxy"
# export HTTPS_PROXY="$https_proxy"

# 确保不会继承环境中残留的代理设置
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY 2>/dev/null || true

# ============================================================
#  ★★★ 配置区 — 请根据你的 API 修改 ★★★
# ============================================================

# LLM 平台: openai / deepseek / qwen / openai-compatible
LLM_PLATFORM="deepseek"

# 模型名称
MODEL_NAME="deepseek-chat"

# API Key
API_KEY="${OASIS_API_KEY:-${OPENAI_API_KEY:-sk-0bd008ab3f8a420c8e795142557cadd2}}"

# API URL（可选，不填则使用平台默认地址）
# 示例:
#   OpenAI 代理:  https://api.gpt.ge/v1
#   DeepSeek:     https://api.deepseek.com/v1
#   本地兼容服务: http://localhost:8000/v1
API_URL=""

# ============================================================
#  社区模拟参数
# ============================================================

NUM_AGENTS=5           # Agent 数量
ROUNDS=3               # 运行轮数 (有限模式)
CONTINUOUS=false       # 持续运行模式 (true/false)
ROUND_DELAY=2.0        # 持续模式轮间延迟(秒)
PLATFORM="twitter"     # 社交平台: twitter / reddit
TEMPERATURE=0.7        # 生成温度

# 外部 Agent 配置（留空则不加载外部 Agent）
# 示例: external_agents_minitimebot.json
EXTERNAL_AGENTS_CONFIG="external_agents_minitimebot.json"

# PsySafe 恶意 Agent（0=不注入）
DARK_AGENTS=0
DARK_PRESET="full_dark"
DARK_EVAL_INTERVAL=0   # 每 N 轮做心理测试 (0=不测试)

# 可视化前端
VIEWER=true            # 启动实时可视化 (true/false)
VIEWER_PORT=8001       # 可视化前端端口

# ============================================================
#  环境准备 (uv)
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"

# uv 缓存放到 /data 分区（根分区空间不足）
export UV_CACHE_DIR="/data/.uv-cache"

# 安装 uv（如果不存在）
if ! command -v uv &>/dev/null; then
    echo "📦 安装 uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# 创建 venv（如果不存在）
if [ ! -d "$VENV_DIR" ]; then
    echo "🐍 创建虚拟环境 ($VENV_DIR)..."
    uv venv "$VENV_DIR" --python 3.11
fi

# 激活 venv
source "$VENV_DIR/bin/activate"

# 安装项目依赖
# 注: 不用 `pip install -e .` 因为 pyproject.toml 硬依赖 sentence-transformers → torch (>5GB)
#     外部 API 模式不需要 torch，只装实际用到的轻量依赖
echo "📦 安装/更新依赖..."
uv pip install --no-build-isolation \
    "camel-ai==0.2.78" \
    "pandas==2.2.2" \
    "igraph==0.11.6" \
    "cairocffi==1.7.1" \
    "pillow==10.3.0" \
    "aiosqlite" \
    || { echo "❌ 依赖安装失败"; exit 1; }

# 以 --no-deps 方式安装 oasis 本身（不触发 sentence-transformers 等重依赖）
uv pip install --no-deps -e . || { echo "❌ oasis 安装失败"; exit 1; }
echo "✅ 依赖就绪"
echo ""

# ============================================================
#  启动
# ============================================================

echo "========================================"
echo "  OASIS 社区模拟 — 外部 API 模式"
echo "========================================"
echo "  平台:     $LLM_PLATFORM"
echo "  模型:     $MODEL_NAME"
echo "  API URL:  ${API_URL:-平台默认}"
echo "  Agents:   $NUM_AGENTS"
echo "  轮数:     $ROUNDS"
echo "  持续模式: $CONTINUOUS"
echo "  外部Agent: ${EXTERNAL_AGENTS_CONFIG:-无}"
echo "  可视化:   $VIEWER (端口 $VIEWER_PORT)"
echo "  Python:   $(python --version)"
echo "  venv:     $VENV_DIR"
echo "========================================"

# DB 路径（模拟和可视化共用）
DB_PATH="./community_simulation.db"

# ── 启动可视化前端（后台） ──
VIEWER_PID=""
if [ "$VIEWER" = "true" ]; then
    echo "🖥️  启动可视化前端 (端口 $VIEWER_PORT)..."
    python community_viewer/live_server.py --db "$DB_PATH" --port "$VIEWER_PORT" &
    VIEWER_PID=$!
    echo "   PID: $VIEWER_PID"
    echo "   浏览器打开: http://localhost:$VIEWER_PORT"
    echo ""
fi

# 退出时清理可视化进程
cleanup() {
    if [ -n "$VIEWER_PID" ] && kill -0 "$VIEWER_PID" 2>/dev/null; then
        echo ""
        echo "🛑 关闭可视化前端 (PID $VIEWER_PID)..."
        kill "$VIEWER_PID" 2>/dev/null || true
        wait "$VIEWER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# 构建命令
CMD="python community_simulation.py"
CMD="$CMD --llm-platform $LLM_PLATFORM"
CMD="$CMD --model-name $MODEL_NAME"
CMD="$CMD --api-key $API_KEY"
CMD="$CMD --num-agents $NUM_AGENTS"
CMD="$CMD --rounds $ROUNDS"
CMD="$CMD --platform $PLATFORM"
CMD="$CMD --temperature $TEMPERATURE"

CMD="$CMD --db-path $DB_PATH"

if [ -n "$API_URL" ]; then
    CMD="$CMD --api-url $API_URL"
fi

if [ "$CONTINUOUS" = "true" ]; then
    CMD="$CMD --continuous --round-delay $ROUND_DELAY"
fi

if [ -n "$EXTERNAL_AGENTS_CONFIG" ] && [ -f "$EXTERNAL_AGENTS_CONFIG" ]; then
    CMD="$CMD --external-agents-config $EXTERNAL_AGENTS_CONFIG"
fi

if [ "$DARK_AGENTS" -gt 0 ]; then
    CMD="$CMD --dark-agents $DARK_AGENTS --dark-preset $DARK_PRESET"
    if [ "$DARK_EVAL_INTERVAL" -gt 0 ]; then
        CMD="$CMD --dark-eval-interval $DARK_EVAL_INTERVAL"
    fi
fi

echo ""
echo "▶ $CMD"
echo ""
$CMD
