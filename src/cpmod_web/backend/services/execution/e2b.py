from __future__ import annotations

import json

from ...config import get_settings
from ...models.domain import ExecutionResult, FailureType
from .base import ExecutionBackend
from .harness import build_execution_files


class E2BExecutionBackend(ExecutionBackend):
    async def execute_model(self, *, code: str, input_data: dict, metadata: dict | None = None) -> ExecutionResult:
        settings = get_settings()
        if not settings.e2b_api_key:
            raise RuntimeError('E2B execution requested but CPMOD_WEB_E2B_API_KEY is not configured.')

        from e2b_code_interpreter import AsyncSandbox

        sandbox_kwargs = {'api_key': settings.e2b_api_key, 'timeout': settings.execution_timeout_seconds}
        if settings.e2b_template:
            sandbox_kwargs['template'] = settings.e2b_template

        async with AsyncSandbox(**sandbox_kwargs) as sandbox:
            files, entry_script = build_execution_files(code=code, input_data=input_data, metadata=metadata)
            for relative_path, content in files.items():
                await sandbox.files.write(f'/home/user/{relative_path}', content)
            result = await sandbox.commands.run(f'python /home/user/{entry_script}', timeout=settings.execution_timeout_seconds)
            stdout = result.stdout or ''
            stderr = result.stderr or ''
            if result.exit_code != 0:
                return ExecutionResult(
                    passed=False,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=int(result.exit_code),
                    error_type=FailureType.RUNTIME_ERROR,
                )
            try:
                parsed = json.loads(stdout)
            except json.JSONDecodeError:
                return ExecutionResult(
                    passed=False,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=int(result.exit_code),
                    error_type=FailureType.OUTPUT_FORMAT,
                )
            return ExecutionResult(
                passed=True,
                stdout=stdout,
                stderr=stderr,
                exit_code=int(result.exit_code),
                parsed_output=parsed,
            )
