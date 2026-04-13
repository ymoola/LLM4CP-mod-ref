from __future__ import annotations

import asyncio

from .db import queries
from .models.domain import FailureType, RunStatus
from .workflow.service import run_workflow

POLL_INTERVAL_SECONDS = 2.5


async def poll_and_run() -> None:
    while True:
        run = queries.claim_pending_run()
        if run:
            try:
                await run_workflow(run['id'])
            except Exception as exc:
                queries.update_workflow_run(
                    run['id'],
                    {
                        'status': RunStatus.FAILED.value,
                        'failure_type': FailureType.INTERNAL_ERROR.value,
                        'last_error': str(exc),
                    },
                )
                queries.add_run_event(
                    {
                        'run_id': run['id'],
                        'stage': 'worker',
                        'outcome': 'failed',
                        'failure_type': FailureType.INTERNAL_ERROR.value,
                        'message': str(exc),
                        'attempt': 1,
                        'payload': {},
                    }
                )
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == '__main__':
    asyncio.run(poll_and_run())
