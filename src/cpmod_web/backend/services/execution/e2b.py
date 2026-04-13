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

        sandbox = await AsyncSandbox.create(**sandbox_kwargs)
        async with sandbox:
            files, entry_script = build_execution_files(code=code, input_data=input_data, metadata=metadata)
            for relative_path, content in files.items():
                await sandbox.files.write(f'/home/user/{relative_path}', content)
            install = await sandbox.commands.run(
                'python -m pip install --quiet cpmpy numpy',
                timeout=min(max(settings.execution_timeout_seconds * 2, 60), 180),
            )
            if install.exit_code != 0:
                return ExecutionResult(
                    passed=False,
                    stdout=install.stdout or '',
                    stderr=install.stderr or 'Failed to install CPMpy inside the E2B sandbox.',
                    exit_code=int(install.exit_code),
                    error_type=FailureType.RUNTIME_ERROR,
                )
            try:
                result = await sandbox.commands.run(f'python /home/user/{entry_script}', timeout=settings.execution_timeout_seconds)
            except Exception as exc:  # pragma: no cover - network/runtime dependent
                message = str(exc)
                error_type = FailureType.TIMEOUT if 'timeout' in message.lower() else FailureType.RUNTIME_ERROR
                return ExecutionResult(
                    passed=False,
                    stdout='',
                    stderr=message,
                    exit_code=124 if error_type == FailureType.TIMEOUT else 1,
                    error_type=error_type,
                    timeout_seconds=settings.execution_timeout_seconds if error_type == FailureType.TIMEOUT else None,
                )
            stdout = result.stdout or ''
            stderr = result.stderr or ''
            if result.exit_code != 0:
                return ExecutionResult(
                    passed=False,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=int(result.exit_code),
                    error_type=FailureType.TIMEOUT if 'timeout' in stderr.lower() else FailureType.RUNTIME_ERROR,
                    timeout_seconds=settings.execution_timeout_seconds if 'timeout' in stderr.lower() else None,
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
