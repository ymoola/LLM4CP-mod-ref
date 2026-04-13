from __future__ import annotations

import ast
import sys
from dataclasses import dataclass

SUPPORTED_THIRD_PARTY_MODULES = {'cpmpy', 'numpy'}
# Common alias import that still resolves to numpy.
SUPPORTED_TOP_LEVEL_MODULES = SUPPORTED_THIRD_PARTY_MODULES | {'np'}


@dataclass(frozen=True)
class DependencyScanResult:
    unsupported_modules: list[str]

    @property
    def is_supported(self) -> bool:
        return not self.unsupported_modules


try:
    STDLIB_MODULES = set(sys.stdlib_module_names)
except AttributeError:  # pragma: no cover
    STDLIB_MODULES = set()


# A few modules can appear in imports on older Python versions or through submodule paths.
STDLIB_MODULES.update(
    {
        '__future__',
        'typing_extensions',
    }
)


def _top_level_module(name: str | None) -> str | None:
    if not name:
        return None
    stripped = name.strip()
    if not stripped:
        return None
    return stripped.split('.')[0]


def scan_supported_imports(code: str) -> DependencyScanResult:
    tree = ast.parse(code)
    unsupported: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = _top_level_module(alias.name)
                if module and module not in STDLIB_MODULES and module not in SUPPORTED_TOP_LEVEL_MODULES:
                    unsupported.add(module)
        elif isinstance(node, ast.ImportFrom):
            if node.level and not node.module:
                continue
            module = _top_level_module(node.module)
            if module and module not in STDLIB_MODULES and module not in SUPPORTED_TOP_LEVEL_MODULES:
                unsupported.add(module)

    return DependencyScanResult(unsupported_modules=sorted(unsupported))


def supported_runtime_description() -> str:
    return 'Python standard library + cpmpy + numpy only.'
