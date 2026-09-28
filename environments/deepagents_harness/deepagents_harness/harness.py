from pathlib import Path

from pydantic import Field

import verifiers.v1 as vf
from verifiers.v1.errors import InterceptionError

PROGRAM_SOURCE = (Path(__file__).resolve().parent / "program.py").read_text()
EXIT_UNREACHABLE = 75
"""program.py's exit code when the interception endpoint could not be reached."""


class DeepAgentsHarnessConfig(vf.HarnessConfig):
    version: str = Field(default="0.7.19", pattern=r"^[A-Za-z0-9._+-]+$")
    """deepagents release to install, pinned for reproducibility."""
    langchain_openai_version: str = Field(default="1.6.6", pattern=r"^[A-Za-z0-9._+-]+$")
    """langchain-openai release used to reach the interception endpoint."""
    recursion_limit: int = Field(default=1000, gt=0)
    """LangGraph step budget; each model call and tool call is one step."""
    max_nudges: int = Field(default=3, ge=0)
    """Times the agent is sent back to work when it stops with uncommitted changes."""


class DeepAgentsHarness(vf.Harness[DeepAgentsHarnessConfig]):
    APPENDS_SYSTEM_PROMPT = True
    SUPPORTS_MCP = False

    @property
    def source(self) -> str:
        return PROGRAM_SOURCE.replace("{version}", self.config.version).replace(
            "{langchain_openai_version}", self.config.langchain_openai_version
        )

    async def setup(self, runtime: vf.Runtime) -> None:
        # activate=False keeps the harness venv out of the agent's shell commands.
        await runtime.prepare_uv_script(self.source, self.config.resolved_env, activate=False)

    async def launch(
        self,
        ctx: vf.ModelContext,
        trace: vf.Trace,
        runtime: vf.Runtime,
        endpoint: str,
        secret: str,
        mcp_urls: dict[str, str],
        data: vf.TaskData,
    ) -> vf.ProgramResult:
        if self.config.disabled_tools:
            raise ValueError("deepagents harness does not support disabling tools")
        system_prompt, prompt = self.resolve_text_prompt(data)
        if prompt is None:
            raise ValueError("deepagents harness requires a task prompt")
        args = [
            f"--base-url={endpoint}",
            f"--api-key={secret}",
            f"--model={ctx.model}",
            f"--system-prompt={system_prompt or ''}",
            f"--task={prompt}",
            f"--tool-timeout={int(self.config.tool_timeout)}",
            f"--recursion-limit={self.config.recursion_limit}",
            f"--max-nudges={self.config.max_nudges}",
        ]
        if data.workdir:
            args.append(f"--workdir={data.workdir}")
        program = await runtime.prepare_uv_script(
            self.source, self.config.resolved_env, activate=False
        )
        result = await runtime.run_program([*program, *args], self.config.resolved_env)
        if result.exit_code == EXIT_UNREACHABLE:
            # Infrastructure, not the agent: surface it as retryable (`retries.include`).
            detail = result.stderr.strip().splitlines()[-1:] or ["<no output>"]
            raise InterceptionError(f"harness {self.config.id!r} lost the interception endpoint: {detail[0]}")
        return result
