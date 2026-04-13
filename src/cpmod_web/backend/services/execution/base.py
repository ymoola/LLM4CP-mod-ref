from __future__ import annotations

from abc import ABC, abstractmethod

from ...models.domain import ExecutionResult


class ExecutionBackend(ABC):
    @abstractmethod
    async def execute_model(self, *, code: str, input_data: dict, metadata: dict | None = None) -> ExecutionResult:
        raise NotImplementedError
