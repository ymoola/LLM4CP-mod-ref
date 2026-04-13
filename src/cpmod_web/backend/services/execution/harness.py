from __future__ import annotations

import json
from textwrap import dedent
from typing import Any


def execution_mode_from_metadata(metadata: dict[str, Any] | None) -> str:
    mode = str((metadata or {}).get('execution_mode') or 'script').strip().lower()
    return mode if mode in {'script', 'build_model'} else 'script'


def build_execution_files(*, code: str, input_data: dict[str, Any], metadata: dict[str, Any] | None) -> tuple[dict[str, str], str]:
    metadata = metadata or {}
    mode = execution_mode_from_metadata(metadata)
    files = {
        'input_data.json': json.dumps(input_data, indent=2),
        'execution_metadata.json': json.dumps(metadata, indent=2),
    }
    if mode == 'build_model':
        files['uploaded_model.py'] = code
        files['runner.py'] = _build_model_runner()
        return files, 'runner.py'
    files['model.py'] = code
    return files, 'model.py'


def execution_contract_text(metadata: dict[str, Any] | None) -> str:
    metadata = metadata or {}
    mode = execution_mode_from_metadata(metadata)
    if mode == 'build_model':
        entrypoint = metadata.get('entrypoint_name') or 'build_model'
        output_names = metadata.get('output_variable_names') or []
        outputs = ', '.join(str(name) for name in output_names) if output_names else '(same returned outputs)'
        return (
            f'- Preserve the module-style execution contract.\n'
            f'- Keep the `{entrypoint}` entrypoint callable from imported Python code.\n'
            f'- The entrypoint must remain solvable using values from `input_data.json`.\n'
            f'- Return the CPMpy model plus output objects corresponding to: {outputs}.\n'
            f'- Do not convert this file into a standalone script unless the change request explicitly asks for that.'
        )
    return (
        '- Read the runtime instance from `input_data.json`.\n'
        '- Print valid JSON as the final output.'
    )


def _build_model_runner() -> str:
    return dedent(
        """
        import importlib.util
        import inspect
        import json
        from pathlib import Path


        def _load_module(path: Path):
            spec = importlib.util.spec_from_file_location("uploaded_model", path)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"Unable to import module from {path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module


        def _call_entrypoint(fn, input_data):
            sig = inspect.signature(fn)
            params = list(sig.parameters.values())
            if not params:
                return fn()
            if isinstance(input_data, dict):
                try:
                    accepts_var_kwargs = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params)
                    if accepts_var_kwargs:
                        bound = sig.bind(**input_data)
                    else:
                        accepted_names = {
                            name
                            for name, param in sig.parameters.items()
                            if param.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
                        }
                        filtered_input = {key: value for key, value in input_data.items() if key in accepted_names}
                        bound = sig.bind(**filtered_input)
                    return fn(*bound.args, **bound.kwargs)
                except TypeError:
                    if len(params) == 1:
                        return fn(input_data)
                    raise
            if len(params) == 1:
                return fn(input_data)
            raise TypeError("input_data.json must be an object matching the entrypoint parameters")


        def _to_serializable(value):
            if hasattr(value, "value") and callable(value.value):
                return _to_serializable(value.value())
            if isinstance(value, dict):
                return {str(k): _to_serializable(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [_to_serializable(v) for v in value]
            if hasattr(value, "tolist"):
                return _to_serializable(value.tolist())
            if hasattr(value, "item") and callable(value.item):
                try:
                    return value.item()
                except Exception:
                    pass
            if isinstance(value, (str, int, float, bool)) or value is None:
                return value
            raise TypeError(f"Value of type {type(value).__name__} is not JSON serializable")


        def _normalize_result(result, metadata):
            output_names = [str(name) for name in metadata.get("output_variable_names") or [] if str(name).strip()]
            if isinstance(result, dict):
                if "model" not in result:
                    raise ValueError("Entrypoint dict return must include a 'model' key")
                model = result["model"]
                outputs = {k: v for k, v in result.items() if k != "model"}
                if output_names:
                    missing = [name for name in output_names if name not in outputs]
                    if missing:
                        raise ValueError(f"Entrypoint result is missing configured outputs: {missing}")
                    outputs = {name: outputs[name] for name in output_names}
                return model, outputs
            if not isinstance(result, (tuple, list)) or not result:
                raise ValueError("Entrypoint must return a tuple/list whose first item is the CPMpy model")
            model = result[0]
            returned = list(result[1:])
            if not output_names:
                raise ValueError("build_model mode requires output_variable_names metadata for tuple/list returns")
            if len(returned) != len(output_names):
                raise ValueError(
                    f"Entrypoint returned {len(returned)} outputs, but output_variable_names has {len(output_names)} names"
                )
            return model, dict(zip(output_names, returned))


        def main():
            workdir = Path(".")
            input_data = json.loads((workdir / "input_data.json").read_text())
            metadata = json.loads((workdir / "execution_metadata.json").read_text())
            entrypoint_name = metadata.get("entrypoint_name") or "build_model"
            module = _load_module(workdir / "uploaded_model.py")
            entrypoint = getattr(module, entrypoint_name, None)
            if entrypoint is None or not callable(entrypoint):
                raise AttributeError(f"Module does not define callable entrypoint '{entrypoint_name}'")
            result = _call_entrypoint(entrypoint, input_data)
            model, outputs = _normalize_result(result, metadata)
            if not hasattr(model, "solve") or not callable(model.solve):
                raise TypeError("Entrypoint did not return a CPMpy model as its first value")
            solved = model.solve()
            if not solved:
                raise RuntimeError("No solution found")
            print(json.dumps({name: _to_serializable(value) for name, value in outputs.items()}))


        if __name__ == "__main__":
            main()
        """
    ).strip() + "\n"
