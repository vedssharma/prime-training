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

3-task smoke run, `deepseek/deepseek-v4-flash`, local Docker, no planning tool:

| Task | Reward | Fail-to-pass | Pass-to-pass |
| --- | --- | --- | --- |
| abs-module-cache-flags | 0 | 11/20 | 3/3 |
| abs-stepped-slices | 0 | 3/6 | 5/6 |
| actionlint-action-pinning-lint | 0 | 55/55 | 144/145 |
