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
from langchain.agents.middleware import AgentMiddleware, TodoListMiddleware, hook_config
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from openai import APIConnectionError, APIStatusError

# Exit code telling the harness the interception endpoint was unreachable (EX_TEMPFAIL).
EXIT_UNREACHABLE = 75

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

NUDGE = """You stopped without calling a tool, but the repository at {workdir} still has uncommitted changes:

{status}
If the task is not finished, continue working. If it is, make sure the work is committed as the task instructs, then stop."""


class UncommittedWorkNudge(AgentMiddleware):
    """Send the model back to work when it ends its turn with uncommitted changes.

    Deep Agents treats any reply without a tool call as the final answer, so a model that
    stops mid-thought (e.g. a long reasoning reply) ends the rollout and loses its work.
    The nudge only asks; it never commits on the agent's behalf.
    """

    def __init__(self, workdir: str, max_nudges: int) -> None:
        super().__init__()
        self.workdir = workdir
        self.max_nudges = max_nudges
        self.nudges = 0

    async def uncommitted(self) -> str:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", self.workdir, "status", "--porcelain",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        # Not a git repository (or no git): nothing to guard.
        return stdout.decode() if proc.returncode == 0 else ""

    @hook_config(can_jump_to=["model"])
    async def aafter_model(self, state, runtime) -> dict | None:
        last = state["messages"][-1]
        if not isinstance(last, AIMessage) or last.tool_calls or self.nudges >= self.max_nudges:
            return None
        status = await self.uncommitted()
        if not status:
            return None
        self.nudges += 1
        print(f"[deepagents] nudge {self.nudges}/{self.max_nudges}: uncommitted changes", file=sys.stderr)
        text = NUDGE.format(workdir=self.workdir, status=status)
        return {"messages": [HumanMessage(text)], "jump_to": "model"}


def unreachable(error: BaseException) -> str | None:
    """Describe `error` if it means the interception endpoint itself could not be reached.

    Covers a dropped connection and a non-JSON error page served in the endpoint's place
    (e.g. a tunnel's "404 Tunnel not found"). JSON errors are real model/provider errors.
    """
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if isinstance(error, APIConnectionError):
            return f"{type(error).__name__}: {error}"
        if isinstance(error, APIStatusError):
            content_type = error.response.headers.get("content-type", "")
            if "json" not in content_type:
                return f"HTTP {error.status_code} with a {content_type or 'non-JSON'} body"
        error = error.__cause__ or error.__context__
    return None


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
    parser.add_argument("--max-nudges", type=int, default=3)
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
        middleware=[
            TodoListMiddleware(),
            UncommittedWorkNudge(args.workdir, args.max_nudges),
        ],
    )
    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": args.task}]},
            config={"recursion_limit": args.recursion_limit},
        )
    except Exception as error:
        if reason := unreachable(error):
            print(f"[deepagents] interception endpoint unreachable: {reason}", file=sys.stderr)
            sys.exit(EXIT_UNREACHABLE)
        raise
    messages = result["messages"]
    print(f"[deepagents] finished after {len(messages)} messages", file=sys.stderr)
    print(messages[-1].text if messages else "")


if __name__ == "__main__":
    asyncio.run(main())
