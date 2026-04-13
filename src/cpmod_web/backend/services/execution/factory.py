from __future__ import annotations

from ...config import get_settings
from .base import ExecutionBackend
from .e2b import E2BExecutionBackend
from .local import LocalExecutionBackend


def get_execution_backend() -> ExecutionBackend:
    settings = get_settings()
    if settings.resolved_execution_backend == 'e2b':
        return E2BExecutionBackend()
    return LocalExecutionBackend()
