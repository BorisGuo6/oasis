#!/bin/bash
set -e

# 代理
export http_proxy="http://star-proxy.oa.com:3128"
export https_proxy="http://star-proxy.oa.com:3128"

# 激活 oasis 环境
source /opt/conda/bin/activate /apdcephfs_nj7/share_303382070/bguo/anaconda3/envs/oasis

echo "=== Python: $(python --version) ==="
echo "=== pip install oasis ==="

cd /apdcephfs_nj7/share_303382070/bguo/oasis
pip install -e . 2>&1 | tail -20

echo "=== pip install vllm camel-ai pandas ==="
pip install vllm camel-ai pandas 2>&1 | tail -20

echo "=== 安装完成，验证 ==="
python -c "import oasis; print('oasis OK')"
python -c "import vllm; print('vllm OK')"
python -c "import camel; print('camel OK')"
pip list | wc -l
echo "=== DONE ==="
