"""Sandboxed Python code execution tool."""
import asyncio
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, Field

from backend.harness.tools.base import BaseTool, register_tool
from models.schemas import get_settings

settings = get_settings()


class RunPythonInput(BaseModel):
    code: str = Field(..., description="Python code to execute. Use print() for output.")
    timeout: int = Field(30, description="Timeout in seconds (max 60)", ge=1, le=60)


class RunPythonTool(BaseTool):
    name: ClassVar[str] = "run_python"
    description: ClassVar[str] = (
        "Execute Python code in a sandboxed subprocess. Use for data processing, "
        "calculations, parsing, analysis, and producing structured output. "
        "Results are captured from stdout. Can import standard library modules. "
        "Network access is available for HTTP requests within the code."
    )
    input_schema: ClassVar[type[BaseModel]] = RunPythonInput

    async def run(self, code: str, timeout: int = 30) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "script.py"
            script_path.write_text(code, encoding="utf-8")

            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(script_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmpdir,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except:
                    pass
                return f"Error: Code execution timed out after {timeout} seconds."
            except Exception as e:
                return f"Error spawning subprocess: {e}"

        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()
        rc = proc.returncode

        parts = []
        if stdout_text:
            # Truncate very long output
            if len(stdout_text) > 3000:
                stdout_text = stdout_text[:3000] + "\n[... output truncated ...]"
            parts.append(f"STDOUT:\n{stdout_text}")

        if stderr_text:
            if len(stderr_text) > 3000:
                stderr_text = stderr_text[:3000] + "\n[... stderr truncated ...]"
            parts.append(f"STDERR:\n{stderr_text}")

        if rc != 0:
            parts.append(f"Return code: {rc} (non-zero indicates error)")
        else:
            parts.append(f"Return code: 0 (success)")

        return "\n\n".join(parts) if parts else "No output produced."


register_tool(RunPythonTool())