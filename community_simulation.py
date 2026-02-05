"""
Oasis Agent 社区 - 内网终极版 (Local Only)
包含 10 个 Agent，使用本地 Qwen3-4B-Instruct-2507 模型
"""

import asyncio
import os
from typing import Dict, List

# 导入必要的库用于打补丁
import oasis.social_platform.platform
import oasis.social_platform.recsys
from camel.models import ModelFactory, ModelManager
from camel.types import ModelPlatformType

import oasis
from oasis import (ActionType, AgentGraph, LLMAction, ManualAction,
                   SocialAgent, UserInfo)

# ===========================================================================
# 🛡️ 内网环境补丁 (Offline Patches)
# ===========================================================================

# 补丁 1: 强制替换推荐系统算法
# 原来的算法会下载 HuggingFace 模型，我们把它替换成纯随机推荐，无需联网
def patched_random_rec(*args, **kwargs):
    # 提取 rec_sys_random 需要的参数 (post_table, rec_matrix, max_rec_post_len)
    # rec_sys_personalized_twh 的参数位置: 1=post_table, 4=rec_matrix, 5=max_rec_post_len
    try:
        post_table = args[1]
        rec_matrix = args[4]
        max_rec_post_len = args[5]
        return oasis.social_platform.recsys.rec_sys_random(post_table, rec_matrix, max_rec_post_len)
    except Exception as e:
        print(f"⚠️ 推荐系统补丁运行警告: {e}, 返回空列表")
        return [[] for _ in range(len(args[4]))] # 返回空的推荐矩阵

# 应用补丁：覆盖原本的 TWHIN 推荐函数
oasis.social_platform.platform.rec_sys_personalized_twh = patched_random_rec
print("✅ 补丁生效：已禁用 HuggingFace 模型下载 (使用随机推荐)")

# 补丁 2: 伪造 TokenCounter (防止下载 tiktoken)
class DummyTokenCounter:
    def count_tokens_from_messages(self, messages):
        return 0 
    def count_tokens(self, text):
        return 0

# ===========================================================================

# Agent 配置数据
AGENT_CONFIGS = [
    {"agent_id": 0, "user_name": "tech_explorer", "name": "Alice", 
     "description": "科技爱好者，喜欢探索新技术", "persona": "对AI和新技术充满热情"},
    {"agent_id": 1, "user_name": "data_scientist", "name": "Bob", 
     "description": "数据科学家，专注于机器学习", "persona": "用数据说话"},
    {"agent_id": 2, "user_name": "ai_researcher", "name": "Charlie", 
     "description": "AI研究员", "persona": "思考AI的未来和伦理"},
    {"agent_id": 3, "user_name": "startup_founder", "name": "Diana", 
     "description": "创业者", "persona": "追求创新和突破"},
    {"agent_id": 4, "user_name": "software_architect", "name": "Eve", 
     "description": "软件架构师", "persona": "注重系统设计"},
    {"agent_id": 5, "user_name": "product_manager", "name": "Frank", 
     "description": "产品经理", "persona": "以用户需求为导向"},
    {"agent_id": 6, "user_name": "devops_engineer", "name": "Grace", 
     "description": "DevOps工程师", "persona": "自动化的忠实信徒"},
    {"agent_id": 7, "user_name": "ux_designer", "name": "Henry", 
     "description": "UX设计师", "persona": "以用户为中心"},
    {"agent_id": 8, "user_name": "security_expert", "name": "Ivy", 
     "description": "安全专家", "persona": "注重安全细节"},
    {"agent_id": 9, "user_name": "tech_writer", "name": "Jack", 
     "description": "技术作家", "persona": "简化复杂技术"}
]


async def create_qwen_model(model_full_path: str, api_url: str = "http://localhost:8000/v1"):
    """创建本地 Qwen 模型实例"""
    model = ModelFactory.create(
        model_platform=ModelPlatformType.VLLM,
        # 🟢 关键修复：vLLM 使用完整路径作为模型名称
        model_type=model_full_path, 
        url=api_url,
        api_key="EMPTY", 
    )
    # 注入 Token 补丁
    model._token_counter = DummyTokenCounter()
    return model


def create_agent(config: dict, model_manager: ModelManager, 
                  available_actions: List[ActionType], 
                  agent_graph: AgentGraph) -> SocialAgent:
    """创建单个 Agent"""
    user_info = UserInfo(
        user_name=config["user_name"],
        name=config["name"],
        description=config["description"],
        profile={"other_info": {"user_profile": config["persona"]}},
        recsys_type="random",  # 显式指定随机
    )
    
    agent = SocialAgent(
        agent_id=config["agent_id"],
        user_info=user_info,
        agent_graph=agent_graph,
        model=model_manager,
        available_actions=available_actions,
    )
    
    agent_graph.add_agent(agent)
    return agent


async def main():
    print("🚀 启动 Oasis Agent 社区...")
    
    # 🟢 1. 配置模型 - 必须与 vLLM 启动参数完全一致
    model_path = "/mnt/shared-storage-user/qianchen1/models/Qwen3-4B-Instruct-2507"
    api_url = "http://localhost:8000/v1"
    
    print(f"📦 连接模型: {model_path}")
    try:
        model = await create_qwen_model(model_path, api_url)
        model_manager = ModelManager(models=[model], scheduling_strategy='round_robin')
        print("✅ 模型连接成功")
    except Exception as e:
        print(f"❌ 模型初始化失败: {e}")
        print("💡 请检查 vLLM 是否使用相同的路径启动")
        return
    
    # 2. 定义可用动作
    available_actions = [
        ActionType.LIKE_POST,
        ActionType.DISLIKE_POST,
        ActionType.CREATE_POST,
        ActionType.CREATE_COMMENT,
        ActionType.FOLLOW,
        ActionType.UNFOLLOW,
    ]
    
    # 3. 创建 AgentGraph 和 Agents
    agent_graph = AgentGraph()
    agents = []
    
    print("👥 创建 10 个 Agents...")
    for config in AGENT_CONFIGS:
        agent = create_agent(config, model_manager, available_actions, agent_graph)
        agents.append(agent)
        print(f"  - Agent {agent.social_agent_id}: {agent.user_info.name}")
    
    # 4. 建立社交关系
    print("🔗 建立社交网络...")
    for i in range(10):
        for j in range(10):
            if i != j and j % 2 == 0:  # 每个 agent 关注一半的其他人
                agent_graph.add_edge(i, j)
    print("✅ 社交网络构建完成")
    
    # 5. 设置数据库
    db_path = "./community_simulation.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    os.environ["OASIS_DB_PATH"] = os.path.abspath(db_path)
    
    # 6. 创建环境
    print("🌐 创建模拟环境...")
    env = oasis.make(
        agent_graph=agent_graph,
        platform=oasis.DefaultPlatformType.TWITTER,
        database_path=db_path,
    )
    
    # 7. 运行模拟
    await env.reset()
    print("✅ 环境准备就绪")
    
    # 初始帖子
    print("📝 发布初始内容...")
    await env.step({
        env.agent_graph.get_agent(0): [
            ManualAction(
                action_type=ActionType.CREATE_POST,
                action_args={"content": "🎉 欢迎来到 Oasis Agent 社区！我们是 10 个AI助手，在这里进行社交互动。"}
            )
        ]
    })
    
    # 运行 3 轮交互
    print("🤖 开始 Agent 交互...")
    for round_num in range(3):
        print(f"  轮次 {round_num + 1}/3")
        actions = {agent: LLMAction() for _, agent in env.agent_graph.get_agents()}
        await env.step(actions)
    
    # 8. 展示结果
    print("\n📊 社区统计:")
    print("=" * 40)
    for i in range(10):
        agent = env.agent_graph.get_agent(i)
        print(f"Agent {i}: {agent.user_info.name} (@{agent.user_info.user_name})")
    
    await env.close()
    print(f"\n✅ 模拟完成！数据库: {db_path}")


if __name__ == "__main__":
    asyncio.run(main())