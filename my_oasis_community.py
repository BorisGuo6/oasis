"""
我的 Oasis Agent 社区模拟
基于 oasis 框架搭建，包含 10 个 agent，使用本地 Qwen3-4B-Instruct-2507 模型
"""

import asyncio
import os
from typing import List

from camel.models import ModelFactory, ModelManager
from camel.types import ModelPlatformType

import oasis
from oasis import (ActionType, AgentGraph, LLMAction, ManualAction,
                   SocialAgent, UserInfo)


async def create_local_qwen_model(model_path: str, api_base: str = "http://localhost:8000/v1"):
    """
    创建本地 Qwen 模型实例
    
    Args:
        model_path: 模型路径，如 /mnt/shared-storage-user/qianchen1/models/Qwen3-4B-Instruct-2507
        api_base: vLLM API 服务器地址
    
    Returns:
        ModelBackend 实例
    """
    return ModelFactory.create(
        model_platform=ModelPlatformType.VLLM,
        model_type="qwen3-4b-instruct",  # vLLM 使用的模型类型名称
        url=api_base,
        model_path=model_path,  # 指定模型路径
    )


def create_community_agents(agent_graph: AgentGraph, 
                           model_manager: ModelManager,
                           available_actions: List[ActionType]) -> List[SocialAgent]:
    """
    创建 10 个社区 agent
    
    Args:
        agent_graph: AgentGraph 实例
        model_manager: 模型管理器
        available_actions: 可用动作列表
    
    Returns:
        创建的 agent 列表
    """
    # 定义 10 个 agent 的配置
    agent_configs = [
        {
            "agent_id": 0,
            "user_name": "tech_explorer",
            "name": "Alice",
            "description": "科技爱好者，喜欢探索新技术和AI",
            "persona": "对新技术充满热情，喜欢分享科技资讯"
        },
        {
            "agent_id": 1,
            "user_name": "data_scientist", 
            "name": "Bob",
            "description": "数据科学家，专注于机器学习和大数据",
            "persona": "数据分析专家，喜欢用数据说话"
        },
        {
            "agent_id": 2,
            "user_name": "ai_researcher",
            "name": "Charlie",
            "description": "AI研究员，致力于推动人工智能发展",
            "persona": "对AI伦理和未来发展有深入思考"
        },
        {
            "agent_id": 3,
            "user_name": "startup_founder",
            "name": "Diana",
            "description": "创业者，正在打造下一个独角兽公司",
            "persona": "充满激情，追求创新和突破"
        },
        {
            "agent_id": 4,
            "user_name": "software_architect",
            "name": "Eve",
            "description": "软件架构师，设计可扩展的系统",
            "persona": "注重系统设计和代码质量"
        },
        {
            "agent_id": 5,
            "user_name": "product_manager",
            "name": "Frank",
            "description": "产品经理，连接用户和技术团队",
            "persona": "以用户需求为导向，追求产品完美"
        },
        {
            "agent_id": 6,
            "user_name": "devops_engineer",
            "name": "Grace",
            "description": "DevOps工程师，专注于自动化和云服务",
            "persona": "追求效率，自动化的忠实信徒"
        },
        {
            "agent_id": 7,
            "user_name": "ux_designer",
            "name": "Henry",
            "description": "UX设计师，创造出色的用户体验",
            "persona": "以用户为中心，追求设计美学"
        },
        {
            "agent_id": 8,
            "user_name": "security_expert",
            "name": "Ivy",
            "description": "安全专家，保护系统免受攻击",
            "persona": "警惕性高，注重安全细节"
        },
        {
            "agent_id": 9,
            "user_name": "tech_writer",
            "name": "Jack",
            "description": "技术作家，将复杂概念变得易懂",
            "persona": "善于沟通，简化复杂技术"
        }
    ]
    
    agents = []
    
    for config in agent_configs:
        # 创建用户信息
        user_info = UserInfo(
            user_name=config["user_name"],
            name=config["name"],
            description=config["description"],
            profile={
                "other_info": {
                    "user_profile": config["persona"]
                }
            },
            recsys_type="twitter",  # 使用 Twitter 类型的社交平台
        )
        
        # 创建 SocialAgent
        agent = SocialAgent(
            agent_id=config["agent_id"],
            user_info=user_info,
            agent_graph=agent_graph,
            model=model_manager,
            available_actions=available_actions,
        )
        
        # 添加到 agent graph
        agent_graph.add_agent(agent)
        agents.append(agent)
    
    return agents


async def setup_agent_interactions(agent_graph: AgentGraph):
    """
    设置 agent 之间的初始交互（关注关系）
    
    Args:
        agent_graph: AgentGraph 实例
    """
    # 创建一个互相关注的社交网络
    for i in range(10):
        for j in range(10):
            if i != j:  # 不关注自己
                # 每个 agent 关注一半的其他 agent
                if j % 2 == 0:
                    agent_graph.add_edge(i, j)


async def main():
    print("🚀 开始创建 Oasis Agent 社区...")
    
    # 1. 配置本地模型
    print("📦 配置本地 Qwen3-4B-Instruct-2507 模型...")
    model_path = "/mnt/shared-storage-user/qianchen1/models/Qwen3-4B-Instruct-2507"
    api_base = "http://localhost:8000/v1"  # 确保 vLLM 服务器在此地址运行
    
    try:
        # 创建本地模型实例
        local_model = await create_local_qwen_model(model_path, api_base)
        
        # 创建模型管理器（可以使用多个模型实例）
        model_manager = ModelManager(
            models=[local_model],
            scheduling_strategy='round_robin',
        )
        print("✅ 模型配置成功")
        
    except Exception as e:
        print(f"❌ 模型配置失败: {e}")
        print("请确保 vLLM 服务器正在运行，地址为: http://localhost:8000/v1")
        return
    
    # 2. 定义可用的社交动作
    available_actions = [
        ActionType.LIKE_POST,
        ActionType.DISLIKE_POST,
        ActionType.CREATE_POST,
        ActionType.CREATE_COMMENT,
        ActionType.FOLLOW,
        ActionType.UNFOLLOW,
        ActionType.REPOST,
    ]
    print(f"✅ 定义了 {len(available_actions)} 种可用社交动作")
    
    # 3. 初始化 AgentGraph
    agent_graph = AgentGraph()
    print("✅ 初始化 AgentGraph 成功")
    
    # 4. 创建 10 个 agent
    print("👥 创建 10 个 Agent 社区成员...")
    agents = create_community_agents(agent_graph, model_manager, available_actions)
    print(f"✅ 成功创建 {len(agents)} 个 Agent")
    
    # 5. 设置初始社交关系
    print("🔗 建立 Agent 之间的社交关系...")
    await setup_agent_interactions(agent_graph)
    print("✅ 社交网络构建完成")
    
    # 6. 设置数据库
    db_path = "./my_oasis_community.db"
    os.environ["OASIS_DB_PATH"] = os.path.abspath(db_path)
    
    # 删除旧数据库（如果存在）
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"🗑️  删除了旧的数据库文件")
    
    # 7. 创建模拟环境
    print("🌐 创建社交平台模拟环境...")
    env = oasis.make(
        agent_graph=agent_graph,
        platform=oasis.DefaultPlatformType.TWITTER,  # 使用 Twitter 平台
        database_path=db_path,
    )
    
    # 8. 重置环境
    await env.reset()
    print("✅ 环境重置完成")
    
    # 9. 执行初始操作
    print("📝 执行初始社交操作...")
    
    # 第一个 agent 创建一条欢迎帖子
    initial_actions = {
        env.agent_graph.get_agent(0): [
            ManualAction(
                action_type=ActionType.CREATE_POST,
                action_args={
                    "content": "🎉 欢迎来到 Oasis Agent 社区！我们是 10 个AI助手，将在这里进行有趣的社交互动和讨论。"
                }
            )
        ]
    }
    await env.step(initial_actions)
    
    # 10. 运行 agent 交互模拟
    print("🤖 运行 Agent 交互模拟...")
    
    # 让所有 agent 进行自主社交行为
    all_agents_actions = {
        agent: LLMAction()  # 使用 LLM 驱动的自主行为
        for _, agent in env.agent_graph.get_agents()
    }
    
    # 运行多轮交互
    for round_num in range(3):  # 运行 3 轮
        print(f"🔄 运行第 {round_num + 1} 轮交互...")
        await env.step(all_agents_actions)
        
        # 额外的手动操作：一些 agent 回复和互动
        if round_num == 0:
            extra_actions = {
                env.agent_graph.get_agent(1): [
                    ManualAction(
                        action_type=ActionType.CREATE_COMMENT,
                        action_args={
                            "post_id": "1",  # 假设第一个帖子ID为1
                            "content": "太棒了！作为数据科学家，我很期待看到这个社区的互动模式！📊"
                        }
                    )
                ],
                env.agent_graph.get_agent(2): [
                    ManualAction(
                        action_type=ActionType.CREATE_COMMENT,
                        action_args={
                            "post_id": "1",
                            "content": "AI 研究员视角：这将是一个研究社交AI行为的好机会！🤖"
                        }
                    )
                ]
            }
            await env.step(extra_actions)
    
    print("✅ 交互模拟完成")
    
    # 11. 展示结果
    print("\n📊 社区模拟结果:")
    print("=" * 50)
    for i in range(10):
        agent = env.agent_graph.get_agent(i)
        print(f"Agent {i}: {agent.user_info.name} (@{agent.user_info.user_name})")
        print(f"  - 描述: {agent.user_info.description}")
        print(f"  - Persona: {agent.user_info.profile['other_info']['user_profile']}")
        print()
    
    # 12. 关闭环境
    await env.close()
    print("🏁 Oasis Agent 社区模拟结束！")
    
    print(f"\n📁 数据库已保存到: {db_path}")
    print("💡 您可以使用数据库查看工具分析 Agent 的交互记录")


async def start_vllm_server():
    """
    启动 vLLM 服务器（如果需要）
    
    注意：您需要先安装 vLLM 并配置好模型
    """
    import subprocess
    
    # vLLM 启动命令
    cmd = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", "/mnt/shared-storage-user/qianchen1/models/Qwen3-4B-Instruct-2507",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--trust-remote-code",  # 对于 Qwen 模型通常是必需的
    ]
    
    print("🚀 启动 vLLM 服务器...")
    print(f"命令: {' '.join(cmd)}")
    
    # 在实际使用时，您可能需要在一个单独的终端运行此命令
    # subprocess.run(cmd)


if __name__ == "__main__":
    # 检查是否需要帮助信息
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
🎯 Oasis Agent 社区使用指南

1. 前置条件：
   - 确保已安装 oasis: pip install -e .
   - 确保已安装 vLLM: pip install vllm
   - 确保模型文件存在: /mnt/shared-storage-user/qianchen1/models/Qwen3-4B-Instruct-2507

2. 启动 vLLM 服务器（在一个单独的终端）：
   python -m vllm.entrypoints.openai.api_server \
     --model /mnt/shared-storage-user/qianchen1/models/Qwen3-4B-Instruct-2507 \
     --host 0.0.0.0 \
     --port 8000 \
     --trust-remote-code

3. 运行社区模拟：
   python my_oasis_community.py

4. 查看结果：
   - 检查控制台输出
   - 查看生成的数据库文件: my_oasis_community.db
   - 查看日志文件: ./log/ 目录
        """)
    else:
        # 运行主程序
        asyncio.run(main())