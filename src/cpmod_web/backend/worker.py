from __future__ import annotations

import asyncio
import logging

from .config import get_settings
from .db import queries
from .models.domain import FailureType, RunStatus
from .workflow.service import run_workflow

POLL_INTERVAL_SECONDS = 2.5
logger = logging.getLogger(__name__)


async def poll_and_run() -> None:
    while True:
        try:
            run = queries.claim_pending_run()
            if run:
                try:
                    await run_workflow(run['id'])
                except Exception as exc:
                    logger.exception('Workflow run %s failed.', run['id'])
                    try:
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
                    except Exception:
                        logger.exception('Failed to persist worker failure state for run %s.', run['id'])
        except Exception:
            logger.exception('Worker poll cycle failed while claiming pending runs.')
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == '__main__':
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )
    settings.validate_for_runtime()
    asyncio.run(poll_and_run())
