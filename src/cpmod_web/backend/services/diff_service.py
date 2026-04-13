from __future__ import annotations

import difflib


def build_unified_diff(*, before: str, after: str, fromfile: str = 'base_model.py', tofile: str = 'generated_model.py') -> str:
    return ''.join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=fromfile,
            tofile=tofile,
        )
    )
