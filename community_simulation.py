"""
Oasis Agent 社区 - 合并版 (Local Only)

合并自：
- community_simulation.py
- community_sim_0115_0204.py
- community_sim_0131_0204.py
- my_oasis_community.py

只保留一个统一入口，支持：
1) 本地 vLLM + Qwen3-4B-Instruct-2507
2) Twitter / Reddit 平台选择
3) 自定义 Agent 数量、轮次、动作与数据库路径
4) 打印 vLLM 启动命令
"""

import argparse
import asyncio
import os
from typing import Dict, List, Optional


DEFAULT_MODEL_RELATIVE = os.path.join(
    os.path.dirname(__file__), "models", "Qwen3-4B-Instruct-2507"
)
DEFAULT_MODEL_FALLBACK = "/mnt/shared-storage-user/qianchen1/models/Qwen3-4B-Instruct-2507"


AGENT_CONFIGS: List[Dict[str, str]] = [
    {"user_name": "tech_explorer", "name": "Alice",
     "description": "科技爱好者，喜欢探索新技术", "persona": "对AI和新技术充满热情"},
    {"user_name": "data_scientist", "name": "Bob",
     "description": "数据科学家，专注于机器学习", "persona": "用数据说话"},
    {"user_name": "ai_researcher", "name": "Charlie",
     "description": "AI研究员", "persona": "思考AI的未来和伦理"},
    {"user_name": "startup_founder", "name": "Diana",
     "description": "创业者", "persona": "追求创新和突破"},
    {"user_name": "software_architect", "name": "Eve",
     "description": "软件架构师", "persona": "注重系统设计"},
    {"user_name": "product_manager", "name": "Frank",
     "description": "产品经理", "persona": "以用户需求为导向"},
    {"user_name": "devops_engineer", "name": "Grace",
     "description": "DevOps工程师", "persona": "自动化的忠实信徒"},
    {"user_name": "ux_designer", "name": "Henry",
     "description": "UX设计师", "persona": "以用户为中心"},
    {"user_name": "security_expert", "name": "Ivy",
     "description": "安全专家", "persona": "注重安全细节"},
    {"user_name": "tech_writer", "name": "Jack",
     "description": "技术作家", "persona": "简化复杂技术"},
]


SIMPLE_ROLES = [
    "社区管理员，喜欢发布公告", "AI技术狂热者", "日常生活分享者",
    "潜水员，偶尔点赞", "激进的评论家", "乐于助人的专家",
    "幽默的段子手", "新闻搬运工", "刚注册的新人", "好奇宝宝",
]


class DummyTokenCounter:
    def count_tokens_from_messages(self, messages):
        return 0

    def count_tokens(self, text):
        return 0


def resolve_model_path(explicit_path: Optional[str]) -> str:
    candidates: List[str] = []
    if explicit_path:
        candidates.append(explicit_path)
    env_path = os.environ.get("OASIS_MODEL_PATH", "").strip()
    if env_path:
        candidates.append(env_path)
    candidates.append(DEFAULT_MODEL_RELATIVE)
    candidates.append(DEFAULT_MODEL_FALLBACK)
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return candidates[0] if candidates else ""


def build_agent_configs(num_agents: int, use_simple_roles: bool) -> List[Dict[str, str]]:
    configs: List[Dict[str, str]] = []
    if use_simple_roles:
        for i in range(num_agents):
            role_desc = SIMPLE_ROLES[i] if i < len(SIMPLE_ROLES) else "普通社区成员"
            configs.append({
                "user_name": f"user_{i}",
                "name": f"User_{i}",
                "description": f"我是User_{i}，我是一个{role_desc}。",
                "persona": role_desc,
            })
    else:
        configs = [dict(c) for c in AGENT_CONFIGS]
        if num_agents > len(configs):
            for i in range(len(configs), num_agents):
                configs.append({
                    "user_name": f"user_{i}",
                    "name": f"User_{i}",
                    "description": "社区成员",
                    "persona": "普通用户",
                })
        else:
            configs = configs[:num_agents]
    return configs


def print_vllm_command(model_path: str, api_url: str, max_model_len: int, gpu_mem_util: float) -> None:
    host, port = "0.0.0.0", "8000"
    if api_url.startswith("http://") or api_url.startswith("https://"):
        try:
            host_port = api_url.split("://", 1)[1].split("/", 1)[0]
            if ":" in host_port:
                host, port = host_port.split(":", 1)
        except Exception:
            pass
    print("\n📦 推荐 vLLM 启动命令：")
    print("python -m vllm.entrypoints.openai.api_server \\")
    print(f"  --model {model_path} \\")
    print(f"  --host {host} \\")
    print(f"  --port {port} \\")
    print("  --trust-remote-code \\")
    print("  --enable-auto-tool-choice \\")
    print("  --tool-call-parser hermes \\")
    print(f"  --max-model-len {max_model_len} \\")
    print(f"  --gpu-memory-utilization {gpu_mem_util}")


async def create_qwen_model(model_type: str, api_url: str, temperature: float):
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType

    model = ModelFactory.create(
        model_platform=ModelPlatformType.VLLM,
        model_type=model_type,
        url=api_url,
        api_key="EMPTY",
        model_config_dict={"temperature": temperature},
    )
    model._token_counter = DummyTokenCounter()
    return model


def apply_offline_patches(oasis_module):
    import oasis.social_platform.platform
    import oasis.social_platform.recsys

    def patched_random_rec(*args, **kwargs):
        try:
            post_table = args[1]
            rec_matrix = args[4]
            max_rec_post_len = args[5]
            return oasis_module.social_platform.recsys.rec_sys_random(
                post_table, rec_matrix, max_rec_post_len
            )
        except Exception as e:
            print(f"⚠️ 推荐系统补丁运行警告: {e}, 返回空列表")
            return [[] for _ in range(len(args[4]))]

    oasis_module.social_platform.platform.rec_sys_personalized_twh = patched_random_rec
    print("✅ 补丁生效：已禁用 HuggingFace 模型下载 (使用随机推荐)")


async def main():
    print("🚀 启动 Oasis Agent 社区（合并版）...")

    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", default=os.environ.get("OASIS_MODEL_PATH", ""))
    parser.add_argument("--model-name", default=os.environ.get("OASIS_VLLM_MODEL_NAME", ""))
    parser.add_argument("--api-url", default=os.environ.get("OASIS_VLLM_URL", "http://localhost:8000/v1"))
    parser.add_argument("--db-path", default=os.environ.get("OASIS_DB_PATH", "./community_simulation.db"))
    parser.add_argument("--rounds", type=int, default=int(os.environ.get("OASIS_COMMUNITY_ROUNDS", "3")))
    parser.add_argument("--num-agents", type=int, default=int(os.environ.get("OASIS_NUM_AGENTS", "10")))
    parser.add_argument("--platform", choices=["twitter", "reddit"],
                        default=os.environ.get("OASIS_PLATFORM", "twitter"))
    parser.add_argument("--recsys-type", choices=["random", "twitter", "reddit"],
                        default=os.environ.get("OASIS_RECSYS_TYPE", ""))
    parser.add_argument("--use-simple-roles", action="store_true",
                        default=os.environ.get("OASIS_SIMPLE_ROLES", "") not in ("", "0", "false", "False"))
    parser.add_argument("--temperature", type=float,
                        default=float(os.environ.get("OASIS_MODEL_TEMPERATURE", "0.7")))
    parser.add_argument("--initial-post",
                        default=os.environ.get(
                            "OASIS_INITIAL_POST",
                            "🎉 欢迎来到 Oasis Agent 社区！我们是 10 个AI助手，在这里进行社交互动。"
                        ))
    parser.add_argument("--topics-csv",
                        default=os.environ.get("OASIS_TOPICS_CSV", "data/twitter_dataset/all_topics.csv"))
    parser.add_argument("--topics-field",
                        default=os.environ.get("OASIS_TOPICS_FIELD", ""))
    parser.add_argument("--topics-num", type=int,
                        default=int(os.environ.get("OASIS_TOPICS_NUM", "3")))
    parser.add_argument("--topics-seed", type=int,
                        default=int(os.environ.get("OASIS_TOPICS_SEED", "42")))
    parser.add_argument("--topics-mode", choices=["initial", "per-round"],
                        default=os.environ.get("OASIS_TOPICS_MODE", "initial"))
    parser.add_argument("--topics-per-round", type=int,
                        default=int(os.environ.get("OASIS_TOPICS_PER_ROUND", "3")))
    parser.add_argument("--extra-comments", action="store_true",
                        default=os.environ.get("OASIS_EXTRA_COMMENTS", "") not in ("", "0", "false", "False"))
    parser.add_argument("--show-agent-summary", action="store_true",
                        default=os.environ.get("OASIS_SHOW_AGENT_SUMMARY", "") not in ("", "0", "false", "False"))
    parser.add_argument("--print-vllm", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.90)
    args = parser.parse_args()

    model_path = resolve_model_path(args.model_path)
    if not model_path or not os.path.exists(model_path):
        print("❌ 未找到本地模型路径。")
        print("请设置环境变量 OASIS_MODEL_PATH，或传入 --model-path。")
        print("例如: export OASIS_MODEL_PATH=/path/to/Qwen3-4B-Instruct-2507")
        return

    if args.print_vllm:
        print_vllm_command(model_path, args.api_url, args.max_model_len, args.gpu_memory_utilization)
        if args.check_only:
            return

    if args.check_only:
        print("✅ 检查完成。")
        return

    import oasis
    from camel.models import ModelManager
    from oasis import (ActionType, AgentGraph, LLMAction, ManualAction,
                       SocialAgent, UserInfo)

    apply_offline_patches(oasis)

    model_type = args.model_name.strip() if args.model_name.strip() else model_path
    print(f"📦 连接模型: {model_path}")
    try:
        model = await create_qwen_model(model_type, args.api_url, args.temperature)
        model_manager = ModelManager(models=[model], scheduling_strategy="round_robin")
        print("✅ 模型连接成功")
    except Exception as e:
        print(f"❌ 模型初始化失败: {e}")
        print("💡 请检查 vLLM 是否使用相同的路径启动")
        return

    available_actions = [
        ActionType.LIKE_POST,
        ActionType.LIKE_COMMENT,
        ActionType.DISLIKE_POST,
        ActionType.CREATE_POST,
        ActionType.CREATE_COMMENT,
        ActionType.FOLLOW,
        ActionType.UNFOLLOW,
        ActionType.REPOST,
    ]

    recsys_type = args.recsys_type.strip()
    if not recsys_type:
        recsys_type = "reddit" if args.platform == "reddit" else "twitter"

    agent_graph = AgentGraph()
    agents = []
    configs = build_agent_configs(args.num_agents, args.use_simple_roles)

    print(f"👥 创建 {len(configs)} 个 Agents...")
    for i, config in enumerate(configs):
        user_info = UserInfo(
            user_name=config["user_name"],
            name=config["name"],
            description=config["description"],
            profile={"other_info": {"user_profile": config["persona"]}} if config.get("persona") else None,
            recsys_type=recsys_type,
        )
        agent = SocialAgent(
            agent_id=i,
            user_info=user_info,
            agent_graph=agent_graph,
            model=model_manager,
            available_actions=available_actions,
        )
        agent_graph.add_agent(agent)
        agents.append(agent)
        print(f"  - Agent {i}: {agent.user_info.name}")

    print("🔗 建立社交网络...")
    for i in range(len(configs)):
        for j in range(len(configs)):
            if i != j and j % 2 == 0:
                agent_graph.add_edge(i, j)
    print("✅ 社交网络构建完成")

    db_path = args.db_path
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
    os.environ["OASIS_DB_PATH"] = os.path.abspath(db_path)

    print("🌐 创建模拟环境...")
    platform_type = oasis.DefaultPlatformType.TWITTER if args.platform == "twitter" else oasis.DefaultPlatformType.REDDIT
    env = oasis.make(
        agent_graph=agent_graph,
        platform=platform_type,
        database_path=db_path,
    )

    await env.reset()
    print("✅ 环境准备就绪")

    print("📝 发布初始内容...")
    initial_actions = {
        env.agent_graph.get_agent(0): [
            ManualAction(
                action_type=ActionType.CREATE_POST,
                action_args={"content": args.initial_post}
            )
        ]
    }

    topics_csv_path = os.path.join(os.path.dirname(__file__), args.topics_csv) if not os.path.isabs(args.topics_csv) else args.topics_csv
    topics_list = []
    if os.path.exists(topics_csv_path):
        try:
            import pandas as pd
            df_topics = pd.read_csv(topics_csv_path)
            topic_col = None
            if args.topics_field and args.topics_field in df_topics.columns:
                topic_col = args.topics_field
            elif "source_tweet" in df_topics.columns:
                topic_col = "source_tweet"
            elif "topic_name" in df_topics.columns:
                topic_col = "topic_name"

            if topic_col:
                df_topics = df_topics.dropna(subset=[topic_col])
                df_topics[topic_col] = df_topics[topic_col].astype(str)
                df_topics = df_topics[df_topics[topic_col].str.strip() != ""]
                if len(df_topics) > 0:
                    if args.topics_num <= 0:
                        sampled = df_topics[topic_col].tolist()
                    else:
                        sampled = df_topics.sample(
                            n=min(args.topics_num, len(df_topics)),
                            random_state=args.topics_seed
                        )[topic_col].tolist()
                    topics_list = sampled
        except Exception as e:
            print(f"⚠️ 读取话题 CSV 失败: {e}")
    else:
        print(f"⚠️ 未找到话题 CSV: {topics_csv_path}")

    # 追加多个话题作为初始帖子
    if topics_list and args.topics_mode == "initial":
        for idx, topic in enumerate(topics_list, start=1):
            initial_actions[env.agent_graph.get_agent(0)].append(
                ManualAction(
                    action_type=ActionType.CREATE_POST,
                    action_args={"content": f"【话题 {idx}】{topic}"}
                )
            )

    await env.step(initial_actions)

    print("🤖 开始 Agent 交互...")
    topic_index = 0
    for round_num in range(args.rounds):
        print(f"  轮次 {round_num + 1}/{args.rounds}")

        if topics_list and args.topics_mode == "per-round":
            # 每轮先发布一批话题
            batch = topics_list[topic_index: topic_index + max(1, args.topics_per_round)]
            if batch:
                topic_index += len(batch)
                topic_actions = {
                    env.agent_graph.get_agent(0): [
                        ManualAction(
                            action_type=ActionType.CREATE_POST,
                            action_args={"content": f"【话题 {topic_index - len(batch) + i + 1}】{topic}"}
                        )
                        for i, topic in enumerate(batch)
                    ]
                }
                await env.step(topic_actions)

        actions = {agent: LLMAction() for _, agent in env.agent_graph.get_agents()}
        await env.step(actions)

        if args.extra_comments and round_num == 0:
            extra_actions = {
                env.agent_graph.get_agent(1): [
                    ManualAction(
                        action_type=ActionType.CREATE_COMMENT,
                        action_args={
                            "post_id": "1",
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
                ],
            }
            await env.step(extra_actions)

    print("\n📊 社区统计:")
    print("=" * 40)
    for i in range(len(configs)):
        agent = env.agent_graph.get_agent(i)
        print(f"Agent {i}: {agent.user_info.name} (@{agent.user_info.user_name})")
        if args.show_agent_summary:
            print(f"  - 描述: {agent.user_info.description}")
            if agent.user_info.profile and "other_info" in agent.user_info.profile:
                persona = agent.user_info.profile["other_info"].get("user_profile", "")
                if persona:
                    print(f"  - Persona: {persona}")

    await env.close()
    print(f"\n✅ 模拟完成！数据库: {db_path}")


if __name__ == "__main__":
    asyncio.run(main())
