#!/bin/bash
set -e

export http_proxy="http://star-proxy.oa.com:3128"
export https_proxy="http://star-proxy.oa.com:3128"

source /opt/conda/bin/activate /apdcephfs_nj7/share_303382070/bguo/anaconda3/envs/oasis

MODEL_DIR=/apdcephfs_nj7/share_303382070/bguo/oasis/models/Qwen3-4B-Instruct-2507
mkdir -p "$MODEL_DIR"

echo "=== 开始下载 Qwen3-4B-Instruct-2507 ==="
python -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='Qwen/Qwen3-4B-Instruct-2507',
    local_dir='$MODEL_DIR',
    resume_download=True
)
print('=== 下载完成 ===')
"
echo "=== 模型文件 ==="
ls -lh "$MODEL_DIR"
