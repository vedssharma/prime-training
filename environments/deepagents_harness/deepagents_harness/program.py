# /// script
# requires-python = ">=3.11"
# dependencies = ["deepagents=={version}", "langchain-openai=={langchain_openai_version}"]
# ///
"""A LangChain Deep Agents coding agent, run inside the task's runtime."""

import argparse
import asyncio
import os
import sys

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from langchain.agents.middleware import TodoListMiddleware
from langchain_openai import ChatOpenAI

SYSTEM_PROMPT = """You are an autonomous software engineer working in a real repository at {workdir}.
Nobody will answer questions: work until the task is fully done, then stop.

How to work:
- Explore before editing: use `ls`, `glob`, `grep` and `read_file` to understand the code and its tests.
- For multi-step work, keep a plan with `write_todos` and update it as you go.
- Make changes with `edit_file` / `write_file`; use `execute` to build, run tests and use git.
- Verify your changes by building and running the relevant tests. Fix what fails.
- Delegate self-contained research (e.g. "find every caller of X") to a subagent with `task` to keep your own context focused.
- Follow any version-control instructions in the task exactly (branch, commit). Only committed work may count.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--system-prompt", default="")
    parser.add_argument("--task", required=True)
    parser.add_argument("--workdir", default=os.getcwd())
    parser.add_argument("--tool-timeout", type=int, default=600)
    parser.add_argument("--recursion-limit", type=int, default=1000)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    model = ChatOpenAI(
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
        # Verifiers' interception server speaks chat completions.
        use_responses_api=False,
        max_retries=3,
        timeout=None,
    )
    backend = LocalShellBackend(
        root_dir=args.workdir,
        # Real paths: the agent works on the task's repository in place.
        virtual_mode=False,
        timeout=args.tool_timeout,
        inherit_env=True,
    )
    system_prompt = SYSTEM_PROMPT.format(workdir=args.workdir)
    if args.system_prompt:
        system_prompt = f"{args.system_prompt}\n\n{system_prompt}"
    agent = create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        backend=backend,
        # deepagents>=0.7 no longer adds the planning tool by default.
        middleware=[TodoListMiddleware()],
    )
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": args.task}]},
        config={"recursion_limit": args.recursion_limit},
    )
    messages = result["messages"]
    print(f"[deepagents] finished after {len(messages)} messages", file=sys.stderr)
    print(messages[-1].text if messages else "")


if __name__ == "__main__":
    asyncio.run(main())
