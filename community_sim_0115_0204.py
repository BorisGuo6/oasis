import asyncio
import os
import random

# 引入 CAMEL 和 OASIS 的必要组件
from camel.models import ModelFactory, ModelManager
from camel.types import ModelPlatformType

import oasis
from oasis import (
    ActionType,
    AgentGraph,
    LLMAction,
    ManualAction,
    SocialAgent,
    UserInfo
)
from oasis.social_platform.typing import RecsysType

async def main():
    # ==========================================
    # 1. 配置模型 (连接到本地 vLLM 服务)
    # ==========================================
    # 注意：确保你已经运行了 vllm serve 命令
    model_path = "Qwen3-4B"  # 对应 --served-model-name 的名称
    server_url = "http://localhost:8000/v1"

    print(f"正在连接本地模型服务: {server_url} ...")
    
    # 使用 ModelFactory 创建模型实例
    # 这里使用 VLLM 平台类型，它兼容 OpenAI 接口格式
    qwen_model = ModelFactory.create(
        model_platform=ModelPlatformType.VLLM,
        model_type=model_path,
        url=server_url,
        model_config_dict={"temperature": 0.7} # 设置温度增加多样性
    )

    # ==========================================
    # 2. 定义 Agent 的可用动作
    # ==========================================
    available_actions = [
        ActionType.CREATE_POST,    # 发帖
        ActionType.create_comment, # 评论 (注意大小写兼容性，通常用 ActionType.CREATE_COMMENT)
        ActionType.LIKE_POST,      # 点赞帖子
        ActionType.LIKE_COMMENT,   # 点赞评论
        ActionType.FOLLOW,         # 关注
    ]
    # 修正：确保使用正确的 ActionType 枚举
    available_actions = [
        ActionType.CREATE_POST,
        ActionType.CREATE_COMMENT,
        ActionType.LIKE_POST,
        ActionType.FOLLOW
    ]

    # ==========================================
    # 3. 初始化 Agent Graph 并添加 10 个 Agent
    # ==========================================
    agent_graph = AgentGraph()
    
    # 定义一些角色描述，让Agent更有个性
    roles = [
        "社区管理员，喜欢发布公告", "AI技术狂热者", "日常生活分享者", 
        "潜水员，偶尔点赞", "激进的评论家", "乐于助人的专家", 
        "幽默的段子手", "新闻搬运工", "刚注册的新人", "好奇宝宝"
    ]

    print("正在初始化 10 个 Agent ...")
    for i in range(10):
        agent_name = f"User_{i}"
        role_desc = roles[i] if i < len(roles) else "普通社区成员"
        
        agent = SocialAgent(
            agent_id=i,
            user_info=UserInfo(
                user_name=agent_name.lower(),
                name=agent_name,
                description=f"我是{agent_name}，我是一个{role_desc}。",
                profile=None,
                recsys_type="reddit", # 使用 reddit 风格推荐系统
            ),
            agent_graph=agent_graph,
            model=qwen_model, # 所有 Agent 复用同一个模型连接
            available_actions=available_actions,
        )
        agent_graph.add_agent(agent)

    # ==========================================
    # 4. 初始化 OASIS 环境
    # ==========================================
    # 数据库路径
    db_path = "./result/my_community_simulation.db"
    os.environ["OASIS_DB_PATH"] = os.path.abspath(db_path)

    # 如果存在旧数据库则删除，重新开始
    if os.path.exists(db_path):
        os.remove(db_path)

    # 创建环境，使用 Reddit 类型的平台（适合社区贴吧模式）
    env = oasis.make(
        agent_graph=agent_graph,
        platform=oasis.DefaultPlatformType.REDDIT,
        database_path=db_path,
    )

    # 重置环境
    print("环境重置中...")
    await env.reset()

    # ==========================================
    # 5. 开始仿真交互
    # ==========================================
    
    # [Step 1] 手动动作：让 Agent 0 发一个欢迎贴，激活社区
    print("Step 1: Agent 0 发布欢迎贴...")
    action_start = {
        env.agent_graph.get_agent(0): [
            ManualAction(
                action_type=ActionType.CREATE_POST,
                action_args={"content": "大家好！欢迎来到我们全新的AI智能体社区。我是管理员，大家可以用Qwen3模型在这里自由交流！"}
            )
        ]
    }
    await env.step(action_start)

    # [Step 2 & 3] 自由交互：让所有 10 个 Agent 根据 LLM 决策行动
    # 进行 3 轮交互
    total_rounds = 3
    for round_num in range(1, total_rounds + 1):
        print(f"Step {round_num + 1}: 所有 Agent 正在思考并行动 (Round {round_num})...")
        
        # 为所有 Agent 生成 LLMAction
        all_agents_actions = {
            agent: LLMAction()
            for _, agent in env.agent_graph.get_agents()
        }
        
        # 执行动作
        await env.step(all_agents_actions)

    # ==========================================
    # 6. 结束仿真
    # ==========================================
    await env.close()
    print("仿真结束。数据已保存至:", db_path)

if __name__ == "__main__":
    asyncio.run(main())