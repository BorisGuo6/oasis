#!/usr/bin/env python3
"""Generate an OASIS discussion schedule YAML from a template pattern.

Usage:
    python generate_schedule.py \
        --pattern debate \
        --num-agents 6 \
        --output schedules/my_debate.yaml

    python generate_schedule.py \
        --pattern roundtable \
        --num-agents 5 \
        --sub-rounds 4 \
        --output schedules/my_roundtable.yaml
"""

import argparse
import os
import sys
from pathlib import Path

import yaml

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "assets" / "templates"

VALID_PATTERNS = ["debate", "brainstorm", "roundtable", "interview"]


def load_template(pattern: str) -> dict:
    """Load a YAML template by pattern name."""
    path = TEMPLATES_DIR / f"{pattern}.yaml"
    if not path.exists():
        print(f"Error: Template not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return yaml.safe_load(f)


def customize_debate(data: dict, num_agents: int) -> dict:
    """Customize debate template for the given agent count."""
    # Layout: 0=mod, 1..mid=side_a, mid+1..N-2=side_b, N-1=observer
    if num_agents < 4:
        print("Warning: Debate needs at least 4 agents. Using 4.", file=sys.stderr)
        num_agents = 4

    mid = (num_agents - 2) // 2  # agents per side
    side_a = list(range(1, 1 + mid))
    side_b = list(range(1 + mid, 1 + 2 * mid))
    observer = num_agents - 1

    data["vars"] = {
        "moderator": 0,
        "side_a": side_a,
        "side_b": side_b,
        "observer": observer,
    }
    return data


def customize_brainstorm(data: dict, num_agents: int) -> dict:
    """Brainstorm uses num_agents directly via expressions, no change needed."""
    return data


def customize_roundtable(data: dict, num_agents: int, sub_rounds: int = 3) -> dict:
    """Customize roundtable template."""
    data.setdefault("vars", {})
    data["vars"]["host"] = 0
    data["vars"]["sub_rounds"] = sub_rounds
    return data


def customize_interview(data: dict, num_agents: int) -> dict:
    """Customize interview template for the given agent count."""
    if num_agents < 2:
        print("Warning: Interview needs at least 2 agents. Using 2.", file=sys.stderr)
        num_agents = 2

    # 1 interviewer, then guests, rest are audience
    num_guests = max(1, min(3, (num_agents - 1) // 2))
    guests = list(range(1, 1 + num_guests))
    audience = list(range(1 + num_guests, num_agents))

    data["vars"] = {
        "interviewer": 0,
        "guests": guests,
        "audience": audience,
    }
    return data


CUSTOMIZERS = {
    "debate": customize_debate,
    "brainstorm": customize_brainstorm,
    "roundtable": customize_roundtable,
    "interview": customize_interview,
}


def main():
    parser = argparse.ArgumentParser(
        description="Generate OASIS discussion schedule YAML"
    )
    parser.add_argument(
        "--pattern",
        required=True,
        choices=VALID_PATTERNS,
        help="Discussion pattern",
    )
    parser.add_argument(
        "--num-agents",
        type=int,
        default=6,
        help="Total number of agents (default: 6)",
    )
    parser.add_argument(
        "--sub-rounds",
        type=int,
        default=3,
        help="Sub-rounds for roundtable pattern (default: 3)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output YAML file path",
    )
    args = parser.parse_args()

    data = load_template(args.pattern)

    kwargs = {"num_agents": args.num_agents}
    if args.pattern == "roundtable":
        kwargs["sub_rounds"] = args.sub_rounds

    data = CUSTOMIZERS[args.pattern](data, **kwargs)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"Generated: {output_path}")
    print(f"Pattern: {args.pattern}, Agents: {args.num_agents}")
    if "vars" in data:
        print(f"Vars: {data['vars']}")


if __name__ == "__main__":
    main()
