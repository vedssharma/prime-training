# prime-training

A [LangChain Deep Agents](https://github.com/langchain-ai/deepagents) coding agent packaged as a [verifiers](https://github.com/PrimeIntellect-ai/verifiers) v1 harness, evaluated on [DeepSWE](https://deepswe.datacurve.ai/) v1.1 with Prime Lab.

## Layout

| Path | What |
| --- | --- |
| [`environments/deepagents_harness`](environments/deepagents_harness) | The harness: `create_deep_agent` + `LocalShellBackend` running inside the task container, model calls routed through the verifiers interception endpoint. |
| [`environments/deep_swe_own`](environments/deep_swe_own) | `primeintellect/deep-swe` with task images read from your own Prime registry namespace, so tasks can run on Prime VM sandboxes. |
| [`configs/eval`](configs/eval) | Eval configs: Prime VMs (`deep-swe-deepagents.toml`) and local Docker (`deep-swe-deepagents-docker.toml`). |

## Setup

```zsh
uv sync
uv pip install "verifiers[harbor]==0.3.1"
# deep-swe is on the Prime Hub index; --no-deps keeps harbor from resolving there
uv pip install --no-deps deep_swe --extra-index-url https://hub.primeintellect.ai/primeintellect/simple/
uv pip install -e environments/deepagents_harness
uv pip install --no-deps -e environments/deep_swe_own
```

## Run

Prime VMs (copy task images into your namespace first; see [`environments/deep_swe_own/README.md`](environments/deep_swe_own/README.md), and set `image_namespace` in the config):

```zsh
uv run eval @ configs/eval/deep-swe-deepagents.toml -n 3
```

Local Docker (pull `public.ecr.aws/d3j8x8q7/swe-bench-202605:<tag>` and re-tag as `prime/prime/swe-bench-202605:<tag>`):

```zsh
uv run eval @ configs/eval/deep-swe-deepagents-docker.toml -n 3
```

## Results so far

Two 3-task smoke runs of `deepseek/deepseek-v4-flash` with provider-default sampling, 1 rollout per task. Reward is DeepSWE's binary pass/fail. The fail-to-pass (F2P) and pass-to-pass (P2P) columns show tests passed out of the total, and the time column is agent wall-clock time.

| Task | Local Docker, no planning tool: F2P / P2P / time | Prime VM, with `write_todos`: F2P / P2P / time |
| --- | --- | --- |
| abs-module-cache-flags | 11/20 · 3/3 · 64 min | 9/20 · 3/3 · 11 min |
| abs-stepped-slices | 3/6 · 5/6 · 26 min | 1/6 · 5/6 · 12 min |
| actionlint-action-pinning-lint | 55/55 · 144/145 · 10 min | 0/55 · 145/145 · 14 min |
| **Solved** | **0/3** | **0/3** |

- **Local Docker** ran amd64 images under emulation on an arm64 Mac, one task at a time. **Prime VMs** run natively, with all 3 tasks in parallel (the whole run took 15 minutes).
- On the VM run, `actionlint-action-pinning-lint` scored 0/55 because the agent never committed. Its last model call was a 39k-token reasoning reply that ended mid-sentence with no tool call, and Deep Agents took that as the final answer. `UncommittedWorkNudge` (added after these runs) now sends the agent back to work in that situation.
- With one rollout per task, differences between the two runs are mostly noise. They validate the pipeline; they don't measure the model.
