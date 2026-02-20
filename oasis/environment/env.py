# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Union

import aiohttp

from oasis.environment.env_action import ExternalAction, LLMAction, ManualAction
from oasis.social_agent.agent import SocialAgent
from oasis.social_agent.agent_graph import AgentGraph
from oasis.social_agent.agents_generator import generate_custom_agents
from oasis.social_platform.channel import Channel
from oasis.social_platform.platform import Platform
from oasis.social_platform.typing import (ActionType, DefaultPlatformType,
                                          RecsysType)

# Create log directory if it doesn't exist
log_dir = "./log"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure logger
env_log = logging.getLogger("oasis.env")
env_log.setLevel("INFO")

# Add file handler to save logs to file
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
file_handler = logging.FileHandler(f"{log_dir}/oasis-{current_time}.log",
                                   encoding="utf-8")
file_handler.setLevel("INFO")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
env_log.addHandler(file_handler)


class OasisEnv:

    def __init__(
        self,
        agent_graph: AgentGraph,
        platform: Union[DefaultPlatformType, Platform],
        database_path: str = None,
        semaphore: int = 128,
    ) -> None:
        r"""Init the oasis environment.

        Args:
            agent_graph: The AgentGraph to use in the simulation.
            platform: The platform type to use. Including
                `DefaultPlatformType.TWITTER` or `DefaultPlatformType.REDDIT`.
                Or you can pass a custom `Platform` instance.
            database_path: The path to create a sqlite3 database. The file
                extension must be `.db` such as `twitter_simulation.db`.
        """
        # Initialize the agent graph
        self.agent_graph = agent_graph
        # Use a semaphore to limit the number of concurrent requests
        self.llm_semaphore = asyncio.Semaphore(semaphore)
        if isinstance(platform, DefaultPlatformType):
            if database_path is None:
                raise ValueError(
                    "database_path is required for DefaultPlatformType")
            self.platform = platform
            if platform == DefaultPlatformType.TWITTER:
                self.channel = Channel()
                self.platform = Platform(
                    db_path=database_path,
                    channel=self.channel,
                    recsys_type="twhin-bert",
                    refresh_rec_post_count=2,
                    max_rec_post_len=2,
                    following_post_count=3,
                )
                self.platform_type = DefaultPlatformType.TWITTER
            elif platform == DefaultPlatformType.REDDIT:
                self.channel = Channel()
                self.platform = Platform(
                    db_path=database_path,
                    channel=self.channel,
                    recsys_type="reddit",
                    allow_self_rating=True,
                    show_score=True,
                    max_rec_post_len=100,
                    refresh_rec_post_count=5,
                )
                self.platform_type = DefaultPlatformType.REDDIT
            else:
                raise ValueError(f"Invalid platform: {platform}. Only "
                                 "DefaultPlatformType.TWITTER or "
                                 "DefaultPlatformType.REDDIT are supported.")
        elif isinstance(platform, Platform):
            if database_path != platform.db_path:
                env_log.warning("database_path is not the same as the "
                                "platform.db_path, using the platform.db_path")
            self.platform = platform
            self.channel = platform.channel
            if platform.recsys_type == RecsysType.REDDIT:
                self.platform_type = DefaultPlatformType.REDDIT
            else:
                self.platform_type = DefaultPlatformType.TWITTER
        else:
            raise ValueError(
                f"Invalid platform: {platform}. You should pass a "
                "DefaultPlatformType or a Platform instance.")

    async def reset(self) -> None:
        r"""Start the platform and sign up the agents."""
        self.platform_task = asyncio.create_task(self.platform.running())
        self.agent_graph = await generate_custom_agents(
            channel=self.channel, agent_graph=self.agent_graph)

    async def _perform_llm_action(self, agent):
        r"""Send the request to the llm model and execute the action.
        """
        async with self.llm_semaphore:
            return await agent.perform_action_by_llm()

    async def _perform_interview_action(self, agent, interview_prompt: str):
        r"""Send the request to the llm model and execute the interview.
        """
        async with self.llm_semaphore:
            return await agent.perform_interview(interview_prompt)

    async def _perform_external_action(
        self, agent: SocialAgent, ext_action: ExternalAction,
    ) -> Any:
        r"""HTTP-call an external agent's endpoint, then execute the returned
        action(s) on behalf of *agent*.

        The external endpoint receives a JSON payload containing the **same
        information** the internal LLM agent sees each round (feed, followers,
        follows, groups).  The internal LLM agent is also stateless — it
        calls ``self.reset()`` every round, so there is no memory of
        previously seen posts.

        Payload::

            {
                "agent_id": <int>,
                "user_name": "<str>",
                "name": "<str>",
                "feed": { ... },          # refresh() — recommended posts
                "num_followers": <int>,
                "num_followings": <int>,
                "groups": { ... },        # group channels / messages
                "round": <int>,           # from extra_context
                ...
            }

        And should return::

            {
                "actions": [
                    {"action": "create_post", "args": {"content": "Hello"}},
                    {"action": "like_post",   "args": {"post_id": 1}},
                    ...
                ]
            }

        If the external agent returns an empty list or ``do_nothing``, one
        ``do_nothing`` is executed.  On timeout / error the agent also does
        nothing.
        """
        aid = agent.social_agent_id

        # 1. Gather the full env snapshot (same info as internal LLM agent)
        try:
            feed = await agent.env.action.refresh()
        except Exception:
            feed = {"success": False, "posts": []}

        # Followers / followings count (mirrors get_followers_env / get_follows_env)
        try:
            followers_text = await agent.env.get_followers_env()
            follows_text = await agent.env.get_follows_env()
            # Parse the numbers back out
            import re
            m_followers = re.search(r"(\d+)", followers_text)
            m_follows = re.search(r"(\d+)", follows_text)
            num_followers = int(m_followers.group(1)) if m_followers else 0
            num_followings = int(m_follows.group(1)) if m_follows else 0
        except Exception:
            num_followers = 0
            num_followings = 0

        # Group info
        try:
            groups = await agent.env.action.listen_from_group()
            if not groups.get("success"):
                groups = {}
        except Exception:
            groups = {}

        payload = {
            "agent_id": aid,
            "user_name": getattr(agent.user_info, "user_name", None),
            "name": getattr(agent.user_info, "name", None),
            "feed": feed,
            "num_followers": num_followers,
            "num_followings": num_followings,
            "groups": groups,
            **ext_action.extra_context,
        }

        # 2. HTTP call
        returned_actions: List[Dict[str, Any]] = []
        try:
            timeout = aiohttp.ClientTimeout(total=ext_action.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    ext_action.endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as resp:
                    if resp.status == 200:
                        body = await resp.json()
                        returned_actions = body.get("actions", [])
                    else:
                        env_log.warning(
                            f"External agent {aid} returned HTTP {resp.status}")
        except asyncio.TimeoutError:
            env_log.warning(
                f"External agent {aid} timed out ({ext_action.timeout}s)")
        except Exception as e:
            env_log.warning(f"External agent {aid} HTTP error: {e}")

        # 3. Execute the returned actions
        if not returned_actions:
            await agent.env.action.do_nothing()
            return

        results = []
        for act_spec in returned_actions:
            action_name = act_spec.get("action", "do_nothing")
            action_args = act_spec.get("args", {})
            try:
                result = await agent.perform_action_by_data(
                    action_name, **action_args)
                results.append(result)
                env_log.info(
                    f"External agent {aid}: {action_name}({action_args}) "
                    f"-> {result}")
            except Exception as e:
                env_log.error(
                    f"External agent {aid}: {action_name} failed: {e}")
        return results

    async def _execute_action(self, agent, action):
        if isinstance(action, ManualAction):
            if action.action_type == ActionType.INTERVIEW:
                interview_prompt = action.action_args.get("prompt", "")
                return await self._perform_interview_action(
                    agent, interview_prompt)
            return await agent.perform_action_by_data(
                action.action_type, **action.action_args)
        if isinstance(action, LLMAction):
            return await self._perform_llm_action(agent)
        if isinstance(action, ExternalAction):
            return await self._perform_external_action(agent, action)
        return None

    async def step(
        self, actions: dict[SocialAgent, Union[ManualAction, LLMAction,
                                               ExternalAction,
                                               List[Union[ManualAction,
                                                          LLMAction,
                                                          ExternalAction]]]]
    ) -> None:
        r"""Update the recommendation system and perform the actions.

        Args:
            actions: The actions to perform, including ManualAction,
                LLMAction, or ExternalAction (HTTP-called external agent).
        Returns:
            None
        """
        # Update the recommendation system
        await self.platform.update_rec_table()
        env_log.info("update rec table.")

        # Create tasks for both manual, LLM, and external actions
        tasks = []
        for agent, action in actions.items():
            if isinstance(action, list):
                for single_action in action:
                    if isinstance(single_action, ManualAction):
                        if single_action.action_type == ActionType.INTERVIEW:
                            interview_prompt = single_action.action_args.get(
                                "prompt", "")
                            tasks.append(
                                self._perform_interview_action(
                                    agent, interview_prompt))
                        else:
                            tasks.append(
                                agent.perform_action_by_data(
                                    single_action.action_type,
                                    **single_action.action_args))
                    elif isinstance(single_action, LLMAction):
                        tasks.append(self._perform_llm_action(agent))
                    elif isinstance(single_action, ExternalAction):
                        tasks.append(
                            self._perform_external_action(agent, single_action))
            else:
                if isinstance(action, ManualAction):
                    if action.action_type == ActionType.INTERVIEW:
                        interview_prompt = action.action_args.get("prompt", "")
                        tasks.append(
                            self._perform_interview_action(
                                agent, interview_prompt))
                    else:
                        tasks.append(
                            agent.perform_action_by_data(
                                action.action_type, **action.action_args))
                elif isinstance(action, LLMAction):
                    tasks.append(self._perform_llm_action(agent))
                elif isinstance(action, ExternalAction):
                    tasks.append(
                        self._perform_external_action(agent, action))

        # Execute all tasks concurrently
        await asyncio.gather(*tasks)
        env_log.info("performed all actions.")
        # Update the clock
        if self.platform_type == DefaultPlatformType.TWITTER:
            self.platform.sandbox_clock.time_step += 1

    async def step_ordered(
        self,
        ordered_actions: List[tuple[SocialAgent, Union[ManualAction, LLMAction,
                                                      ExternalAction,
                                                      List[Union[ManualAction,
                                                                 LLMAction,
                                                                 ExternalAction]]]]],
    ) -> None:
        r"""Perform actions sequentially in the given order.

        Args:
            ordered_actions: List of (agent, action) tuples executed in order.
        """
        await self.platform.update_rec_table()
        env_log.info("update rec table.")

        for agent, action in ordered_actions:
            if isinstance(action, list):
                for single_action in action:
                    await self._execute_action(agent, single_action)
            else:
                await self._execute_action(agent, action)

        env_log.info("performed all ordered actions.")
        if self.platform_type == DefaultPlatformType.TWITTER:
            self.platform.sandbox_clock.time_step += 1

    async def close(self) -> None:
        r"""Stop the platform and close the environment.
        """
        await self.channel.write_to_receive_queue(
            (None, None, ActionType.EXIT))
        await self.platform_task
        env_log.info("Simulation finished! Please check the results in the "
                     f"database: {self.platform.db_path}. Note that the trace "
                     "table stored all the actions of the agents.")
