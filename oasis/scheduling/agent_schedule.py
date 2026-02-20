from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from yaml import safe_load

from oasis.environment.env_action import LLMAction, ManualAction, ParallelGroup
from oasis.social_agent.agent import SocialAgent
from oasis.social_agent.agent_graph import AgentGraph
from oasis.social_platform.typing import ActionType


class ScheduleError(ValueError):
    pass


_EXPR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _safe_eval(expr: str, env: Dict[str, Any]) -> Any:
    allowed_funcs = {
        "range": range,
        "len": len,
        "min": min,
        "max": max,
        "int": int,
        "float": float,
        "bool": bool,
    }
    allowed_names = set(env.keys()) | set(allowed_funcs.keys())

    class _Validator(ast.NodeVisitor):
        allowed_nodes = (
            ast.Expression,
            ast.BoolOp,
            ast.BinOp,
            ast.UnaryOp,
            ast.Compare,
            # operators / comparators
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.FloorDiv,
            ast.Mod,
            ast.Pow,
            ast.And,
            ast.Or,
            ast.Eq,
            ast.NotEq,
            ast.Lt,
            ast.LtE,
            ast.Gt,
            ast.GtE,
            ast.In,
            ast.NotIn,
            ast.Is,
            ast.IsNot,
            ast.UAdd,
            ast.USub,
            ast.Not,
            ast.Name,
            ast.Constant,
            ast.List,
            ast.Tuple,
            ast.Dict,
            ast.Subscript,
            ast.Load,
            ast.Call,
            ast.Slice,
        )

        def generic_visit(self, node):
            if not isinstance(node, self.allowed_nodes):
                raise ScheduleError(f"Unsupported expression node: {type(node).__name__}")
            super().generic_visit(node)

        def visit_Name(self, node: ast.Name):
            if node.id not in allowed_names:
                raise ScheduleError(f"Unknown name in expression: {node.id}")

        def visit_Call(self, node: ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in allowed_funcs:
                raise ScheduleError("Only simple function calls are allowed in expressions.")
            for arg in node.args:
                self.visit(arg)

        def visit_Attribute(self, node: ast.Attribute):
            raise ScheduleError("Attribute access is not allowed in expressions.")

    tree = ast.parse(expr, mode="eval")
    _Validator().visit(tree)
    return eval(compile(tree, "<schedule>", "eval"), {"__builtins__": {}}, {**env, **allowed_funcs})


def _render_value(value: Any, env: Dict[str, Any]) -> Any:
    if isinstance(value, str):
        value = value.strip()
        # Pure expression
        if value.startswith("${") and value.endswith("}") and value.count("${") == 1:
            return _safe_eval(value[2:-1], env)

        # Template string with one or more expressions
        def _replace(match: re.Match) -> str:
            return str(_safe_eval(match.group(1), env))

        rendered = _EXPR_PATTERN.sub(_replace, value)
        # Try to cast numeric strings to int
        if rendered.isdigit():
            return int(rendered)
        return rendered
    if isinstance(value, list):
        return [_render_value(v, env) for v in value]
    if isinstance(value, dict):
        return {k: _render_value(v, env) for k, v in value.items()}
    return value


def _resolve_agent_ids(spec: Dict[str, Any], env: Dict[str, Any]) -> List[int]:
    if "agent" in spec:
        agent_id = _render_value(spec["agent"], env)
        return [int(agent_id)]
    if "agents" in spec:
        rendered = _render_value(spec["agents"], env)
        if isinstance(rendered, list):
            return [int(v) for v in rendered]
        return [int(rendered)]
    if "range" in spec:
        raw = spec["range"]
        if isinstance(raw, dict):
            start = _render_value(raw.get("start", 0), env)
            end = _render_value(raw.get("end", -1), env)
            step = _render_value(raw.get("step", 1), env)
        else:
            start = _render_value(raw[0], env)
            end = _render_value(raw[1], env)
            step = _render_value(raw[2], env) if len(raw) > 2 else 1
        return list(range(int(start), int(end) + 1, int(step)))
    if "group" in spec:
        group_name = spec["group"]
        groups = env.get("vars", {})
        if group_name not in groups:
            raise ScheduleError(f"Unknown group: {group_name}")
        return [int(v) for v in groups[group_name]]
    raise ScheduleError("Agent spec must include one of: agent, agents, range, group.")


@dataclass
class AgentSchedule:
    plan: List[Dict[str, Any]]
    vars: Dict[str, Any]

    @classmethod
    def from_file(cls, path: str | Path) -> "AgentSchedule":
        path = Path(path)
        data = safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ScheduleError("Schedule file must be a YAML mapping.")
        plan = data.get("plan")
        if not isinstance(plan, list):
            raise ScheduleError("Schedule file must include a list field: plan.")
        vars_block = data.get("vars", {}) or {}
        if not isinstance(vars_block, dict):
            raise ScheduleError("vars must be a mapping.")
        return cls(plan=plan, vars=vars_block)

    def build_actions(
        self,
        agent_graph: AgentGraph,
        round_num: int = 1,
        step_num: int | None = None,
    ) -> List[Tuple[SocialAgent, LLMAction | ManualAction | List[ManualAction]]]:
        env: Dict[str, Any] = {
            "round": round_num,
            "step": step_num if step_num is not None else round_num,
            "num_agents": agent_graph.get_num_nodes(),
            "vars": dict(self.vars),
        }
        ordered_actions: List[
            Tuple[SocialAgent, LLMAction | ManualAction | List[ManualAction]]
        ] = []
        self._eval_statements(self.plan, env, agent_graph, ordered_actions)
        return ordered_actions

    def _eval_statements(
        self,
        statements: List[Dict[str, Any]],
        env: Dict[str, Any],
        agent_graph: AgentGraph,
        ordered_actions: List[
            Tuple[SocialAgent, LLMAction | ManualAction | List[ManualAction]]
        ],
    ) -> None:
        for stmt in statements:
            if not isinstance(stmt, dict) or not stmt:
                raise ScheduleError(f"Each statement must be a mapping. Got: {stmt}")

            # Allow compact YAML forms like:
            # - for_each: {...}
            #   do: [...]
            # - if: {...}
            #   then: [...]
            #   else: [...]
            if len(stmt) != 1:
                if "for_each" in stmt:
                    key = "for_each"
                    value = dict(stmt["for_each"] or {})
                    if "do" in stmt and "do" not in value:
                        value["do"] = stmt["do"]
                elif "if" in stmt:
                    key = "if"
                    value = dict(stmt["if"] or {})
                    if "then" in stmt and "then" not in value:
                        value["then"] = stmt["then"]
                    if "else" in stmt and "else" not in value:
                        value["else"] = stmt["else"]
                elif "repeat" in stmt:
                    key = "repeat"
                    value = dict(stmt["repeat"] or {})
                    if "do" in stmt and "do" not in value:
                        value["do"] = stmt["do"]
                elif "parallel" in stmt:
                    key = "parallel"
                    value = stmt["parallel"]
                else:
                    raise ScheduleError(
                        f"Each statement must be a single-key mapping. Got: {stmt}"
                    )
            else:
                key, value = next(iter(stmt.items()))

            if key in {"llm", "speak"}:
                spec = value if isinstance(value, dict) else {"agent": value}
                agent_ids = _resolve_agent_ids(spec, env)
                for agent_id in agent_ids:
                    ordered_actions.append((agent_graph.get_agent(agent_id), LLMAction()))
                continue

            if key == "manual":
                if not isinstance(value, dict):
                    raise ScheduleError("manual statement must be a mapping.")
                agent_ids = _resolve_agent_ids(value, env)
                action_type_raw = value.get("action_type")
                if not action_type_raw:
                    raise ScheduleError("manual statement missing action_type.")
                action_type = ActionType(action_type_raw)
                action_args = _render_value(value.get("action_args", {}), env)
                for agent_id in agent_ids:
                    ordered_actions.append(
                        (agent_graph.get_agent(agent_id),
                         ManualAction(action_type=action_type, action_args=action_args))
                    )
                continue

            if key == "if":
                if not isinstance(value, dict):
                    raise ScheduleError("if statement must be a mapping.")
                condition = value.get("condition", "")
                if not condition:
                    raise ScheduleError("if statement missing condition.")
                result = bool(_safe_eval(condition, env))
                branch = value.get("then" if result else "else", [])
                if branch:
                    self._eval_statements(branch, env, agent_graph, ordered_actions)
                continue

            if key == "for_each":
                if not isinstance(value, dict):
                    raise ScheduleError("for_each statement must be a mapping.")
                var_name = value.get("var", "item")
                iterable_spec = value.get("in")
                if iterable_spec is None:
                    raise ScheduleError("for_each statement missing 'in'.")
                iterable = self._resolve_iterable(iterable_spec, env)
                body = value.get("do", [])
                for item in iterable:
                    env[var_name] = item
                    self._eval_statements(body, env, agent_graph, ordered_actions)
                env.pop(var_name, None)
                continue

            if key == "repeat":
                if not isinstance(value, dict):
                    raise ScheduleError("repeat statement must be a mapping.")
                times = int(_render_value(value.get("times", 0), env))
                body = value.get("do", [])
                for _ in range(times):
                    self._eval_statements(body, env, agent_graph, ordered_actions)
                continue

            if key == "set":
                if not isinstance(value, dict):
                    raise ScheduleError("set statement must be a mapping.")
                var_name = value.get("var")
                if not var_name:
                    raise ScheduleError("set statement missing var.")
                env[var_name] = _render_value(value.get("value"), env)
                continue

            if key == "parallel":
                spec = value if isinstance(value, dict) else {"agents": value}
                agent_ids = _resolve_agent_ids(spec, env)
                group_items = [
                    (agent_graph.get_agent(aid), LLMAction())
                    for aid in agent_ids
                ]
                ordered_actions.append((None, ParallelGroup(items=group_items)))
                continue

            raise ScheduleError(f"Unknown statement type: {key}")

    @staticmethod
    def _resolve_iterable(spec: Any, env: Dict[str, Any]) -> Iterable[Any]:
        if isinstance(spec, dict) and "range" in spec:
            return _resolve_agent_ids({"range": spec["range"]}, env)
        if isinstance(spec, list):
            return [_render_value(v, env) for v in spec]
        if isinstance(spec, str):
            rendered = _render_value(spec, env)
            if isinstance(rendered, list):
                return rendered
            if isinstance(rendered, str):
                return _safe_eval(rendered, env)
            return rendered
        return spec
