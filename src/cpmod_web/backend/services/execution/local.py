from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from ...config import get_settings
from ...models.domain import ExecutionResult, FailureType
from .base import ExecutionBackend
from .harness import build_execution_files


class LocalExecutionBackend(ExecutionBackend):
    async def execute_model(self, *, code: str, input_data: dict, metadata: dict | None = None) -> ExecutionResult:
        settings = get_settings()
        runtime_root = Path(settings.local_executor_workdir)
        runtime_root.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(dir=runtime_root) as tmp_dir:
            workdir = Path(tmp_dir)
            files, entry_script = build_execution_files(code=code, input_data=input_data, metadata=metadata)
            for relative_path, content in files.items():
                (workdir / relative_path).write_text(content)

            proc = await asyncio.create_subprocess_exec(
                'python3',
                entry_script,
                cwd=str(workdir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=settings.execution_timeout_seconds)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ExecutionResult(
                    passed=False,
                    stdout='',
                    stderr='Execution timed out.',
                    exit_code=124,
                    error_type=FailureType.TIMEOUT,
                    timeout_seconds=settings.execution_timeout_seconds,
                )

            stdout = stdout_b.decode('utf-8')
            stderr = stderr_b.decode('utf-8')
            if proc.returncode != 0:
                return ExecutionResult(
                    passed=False,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=int(proc.returncode),
                    error_type=FailureType.RUNTIME_ERROR,
                )

            try:
                parsed = json.loads(stdout)
            except json.JSONDecodeError:
                return ExecutionResult(
                    passed=False,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=int(proc.returncode or 0),
                    error_type=FailureType.OUTPUT_FORMAT,
                )

            return ExecutionResult(
                passed=True,
                stdout=stdout,
                stderr=stderr,
                exit_code=int(proc.returncode or 0),
                parsed_output=parsed,
            )
