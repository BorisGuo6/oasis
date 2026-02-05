#!/usr/bin/env python3
"""
Oasis Agent 社区快速启动脚本 (vLLM Tool Support Enabled)
"""

import subprocess
import sys
import os

def check_dependencies():
    """检查依赖是否安装"""
    print("🔍 检查依赖...")
    required_packages = ['camel', 'vllm', 'pandas']
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            missing.append(package)
            print(f"  ❌ {package}")
    if missing:
        print(f"\n⚠️  缺少依赖: {', '.join(missing)}")
        return False
    return True

def check_model():
    """检查模型文件是否存在"""
    model_path = "/mnt/shared-storage-user/qianchen1/models/Qwen3-4B-Instruct-2507"
    print(f"🔍 检查模型文件...")
    if os.path.exists(model_path):
        print(f"  ✅ 模型路径存在: {model_path}")
        return True
    else:
        print(f"  ❌ 模型路径不存在: {model_path}")
        return False

def main():
    print("=" * 60)
    print("🚀 Oasis Agent 社区启动器")
    print("=" * 60)
    
    if not check_dependencies() or not check_model():
        sys.exit(1)
    
    # 🟢 关键修改：添加了支持 Tool Choice 的 flag
    # --enable-auto-tool-choice: 允许 agent 自动选择工具
    # --tool-call-parser hermes: 指定工具解析格式 (hermes 对 Qwen/ChatML 兼容性较好)
    print("\n📦 [重要] 请使用以下命令重启 vLLM 服务器：")
    print("-" * 60)
    print("python -m vllm.entrypoints.openai.api_server \\")
    print("  --model /mnt/shared-storage-user/qianchen1/models/Qwen3-4B-Instruct-2507 \\")
    print("  --host 0.0.0.0 \\")
    print("  --port 8000 \\")
    print("  --trust-remote-code \\")
    print("  --enable-auto-tool-choice \\")
    print("  --tool-call-parser hermes")
    print("-" * 60)
    
    print("\n⚠️  请务必先停止旧的 vLLM 服务器！")
    input("👉 在另一个终端运行上述命令后，按 Enter 继续...")
    
    print("🏃 运行社区模拟...")
    os.chdir("/mnt/shared-storage-user/qianchen1/junyao/multi-agent/oasis")
    
    # 运行包含补丁的模拟脚本
    cmd = [sys.executable, "community_simulation.py"]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n🎉 社区模拟完成！")
        print("📁 查看数据库文件: community_simulation.db")
    except subprocess.CalledProcessError as e:
        print(f"❌ 模拟失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()