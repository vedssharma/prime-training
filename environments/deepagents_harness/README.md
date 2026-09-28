# deepagents-harness

A coding agent built with [LangChain Deep Agents](https://github.com/langchain-ai/deepagents), packaged as a verifiers v1 harness.

## Agent

`create_deep_agent` with a `LocalShellBackend` rooted at the task's workdir (real paths, `virtual_mode=False`). It runs inside the task container, so the agent gets the standard Deep Agents toolset against the actual repository:

- `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`: file operations
- `execute`: shell commands (timeout = `harness.tool_timeout`)
- `write_todos`: planning (via `TodoListMiddleware`)
- `task`: general-purpose subagents with isolated context

Deep Agents treats any reply without a tool call as the final answer, so a model that stops mid-thought ends the rollout and loses uncommitted work. `UncommittedWorkNudge` catches that: if the model stops while `git status` in the workdir shows uncommitted changes, it sends the model back to work with a reminder (up to `max_nudges` times). It never commits on the agent's behalf, and it does not apply inside `task` subagents.

The model is `ChatOpenAI` over chat completions, pointed at the verifiers interception `endpoint`/`secret`, so every call is captured in the trace. The program is a PEP 723 uv script (`program.py`) prepared with `activate=False`, so the harness venv stays out of the agent's shell.

## Config

| Field | Default | Meaning |
| --- | --- | --- |
| `version` | `0.7.19` | `deepagents` release |
| `langchain_openai_version` | `1.6.6` | `langchain-openai` release |
| `recursion_limit` | `1000` | LangGraph step budget |
| `max_nudges` | `3` | Times the agent is sent back when it stops with uncommitted changes |
| `tool_timeout` | `600` | `execute` timeout, in seconds |

MCP servers, user simulation and `disabled_tools` are not supported.

## Usage

```zsh
uv run eval @ configs/eval/deep-swe-deepagents.toml -n 3
# or
uv run eval primeintellect/deep-swe -m deepseek/deepseek-v4-flash \
  --env.agent.harness.id deepagents-harness \
  --env.agent.runtime.type prime --env.verifier-runtime.type prime
```
