#!/usr/bin/env python3
"""Generate an external agents JSON config for OASIS.

Usage:
    python generate_agents_config.py \
        --roles "主持人,正方辩手A,正方辩手B,反方辩手A,反方辩手B,观察员" \
        --api-url http://localhost:8000/v1 \
        --model gpt-4o \
        --api-key sk-xxx \
        --output external_agents.json

    python generate_agents_config.py \
        --roles "Interviewer,Expert Guest,Audience" \
        --topic "AI Ethics" \
        --output interview_agents.json
"""

import argparse
import json
import sys
from pathlib import Path

# Default persona templates keyed by common role names
ROLE_PERSONAS = {
    "主持人": {
        "description": "Discussion moderator who guides the conversation",
        "persona": "你是一位经验丰富的讨论主持人。你的职责是引导讨论方向、总结各方观点、提出引导性问题推进讨论。请用简洁清晰的语言主持讨论。",
    },
    "moderator": {
        "description": "Discussion moderator who guides the conversation",
        "persona": "You are an experienced discussion moderator. Guide the conversation, summarize viewpoints, and ask leading questions to advance the discussion.",
    },
    "正方辩手": {
        "description": "Argues in favor of the proposition",
        "persona": "你是正方辩手，坚定支持讨论议题。提出有力论据，用事实和逻辑反驳反方观点，保持理性和说服力。",
    },
    "反方辩手": {
        "description": "Argues against the proposition",
        "persona": "你是反方辩手，坚定反对讨论议题。指出正方论点的漏洞和不足，提供替代方案或不同视角。",
    },
    "观察员": {
        "description": "Observes the discussion and provides summaries",
        "persona": "你是讨论观察员。仔细观察所有发言，识别关键论点和分歧，提供中立总结，指出尚未充分探讨的方面。",
    },
    "专家": {
        "description": "Subject matter expert providing authoritative insights",
        "persona": "你是该领域的资深专家。从专业角度分析问题，引用相关研究和数据支持观点，提供深度洞察。",
    },
    "采访者": {
        "description": "Asks insightful questions to draw out information",
        "persona": "你是一位出色的采访者。提出有深度的开放性问题，根据回答追问细节，引导对话深入。",
    },
}


def make_username(role: str) -> str:
    """Convert a role name to a username-friendly string."""
    return role.lower().replace(" ", "_").replace("（", "").replace("）", "")


def generate_agent(
    role: str,
    index: int,
    api_url: str,
    model: str,
    api_key: str,
    platform_type: str,
    temperature: float,
    topic: str = "",
) -> dict:
    """Generate a single agent config dict."""
    base_role = role
    for key in ROLE_PERSONAS:
        if key in role:
            base_role = key
            break

    defaults = ROLE_PERSONAS.get(
        base_role,
        {
            "description": f"Discussion participant: {role}",
            "persona": f"你是讨论参与者，角色是{role}。积极参与讨论，提出你的观点和见解。",
        },
    )

    persona = defaults["persona"]
    if topic:
        persona += f"\n\n讨论主题：{topic}"

    return {
        "api_url": api_url,
        "model": model,
        "api_key": api_key,
        "platform_type": platform_type,
        "temperature": temperature,
        "name": role,
        "user_name": f"{make_username(role)}_{index}",
        "description": defaults["description"],
        "persona": persona,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate OASIS external agent config JSON"
    )
    parser.add_argument(
        "--roles",
        required=True,
        help="Comma-separated role names (e.g. '主持人,正方辩手,反方辩手')",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000/v1",
        help="API endpoint (default: http://localhost:8000/v1)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="Model name (default: gpt-4o)",
    )
    parser.add_argument(
        "--api-key",
        default="sk-placeholder",
        help="API key",
    )
    parser.add_argument(
        "--platform-type",
        default="openai-compatible",
        help="Platform type (default: openai-compatible)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Temperature (default: 0.7)",
    )
    parser.add_argument(
        "--topic",
        default="",
        help="Discussion topic (appended to persona)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file path",
    )
    args = parser.parse_args()

    roles = [r.strip() for r in args.roles.split(",") if r.strip()]
    if not roles:
        print("Error: No roles specified.", file=sys.stderr)
        sys.exit(1)

    agents = []
    for i, role in enumerate(roles):
        agent = generate_agent(
            role=role,
            index=i,
            api_url=args.api_url,
            model=args.model,
            api_key=args.api_key,
            platform_type=args.platform_type,
            temperature=args.temperature,
            topic=args.topic,
        )
        agents.append(agent)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(agents, f, ensure_ascii=False, indent=4)

    print(f"Generated {len(agents)} agent config(s): {output_path}")
    for a in agents:
        print(f"  - {a['name']} ({a['user_name']})")


if __name__ == "__main__":
    main()
