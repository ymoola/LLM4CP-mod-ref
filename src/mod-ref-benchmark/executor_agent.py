import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path


def run_model(model_path: Path, timeout: int | None = None) -> dict:
    """
    Execute a Python model file from its containing directory and parse JSON stdout.
    Raises RuntimeError on non-zero exit, ValueError on JSON parse issues.
    """
    model_dir = model_path.parent
    model_file = model_path.name

    result = subprocess.run(
        [sys.executable, model_file],
        cwd=model_dir,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Execution failed (code {result.returncode}):\n{result.stderr}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model output is not valid JSON: {exc}\nStdout:\n{result.stdout}") from exc


def run_executor_agent(
    problem_path: str,
    cr_name: str,
    model_filename: str = "generated_model.py",
    timeout: int | None = None,
) -> tuple[dict, Path]:
    problem_dir = Path(problem_path)
    cr_dir = problem_dir / cr_name
    model_path = cr_dir / model_filename

    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found at {model_path}")

    model_output = run_model(model_path, timeout=timeout)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log = {
        "problem": problem_dir.name,
        "cr": cr_name,
        "model": model_filename,
        "timestamp": timestamp,
        "result": "success",
        "output": model_output,
    }

    log_path = cr_dir / f"{problem_dir.name}_{cr_name}_executor_log_{timestamp}.json"
    log_path.write_text(json.dumps(log, indent=2))

    return model_output, log_path


def main():
    parser = argparse.ArgumentParser(
        description="Executor agent: run a generated CPMPy model and ensure it produces valid JSON."
    )
    parser.add_argument("--problem", required=True, help="Path to the problem folder (e.g., problems/problem1)")
    parser.add_argument("--cr", required=True, help="Change request folder name (e.g., CR1)")
    parser.add_argument(
        "--model-filename",
        default="generated_model.py",
        help="Model filename inside the CR folder to execute.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="Optional timeout in seconds for model execution.",
    )

    args = parser.parse_args()
    output, log_path = run_executor_agent(
        problem_path=args.problem,
        cr_name=args.cr,
        model_filename=args.model_filename,
        timeout=args.timeout,
    )

    print(f"Execution succeeded. Log saved to {log_path}")
    print(f"Model output keys: {list(output.keys())}")


if __name__ == "__main__":
    main()
