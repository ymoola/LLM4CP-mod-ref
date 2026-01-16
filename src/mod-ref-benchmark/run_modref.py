import os
import sys
import json
import subprocess
import importlib.util
import datetime
import argparse
from llm_generator import generate_model


class GenerationFailed(RuntimeError):
    def __init__(self, attempts, last_error):
        super().__init__(f"Model failed after {attempts} attempts. Last error: {last_error}")
        self.attempts = attempts
        self.last_error = last_error


def load_verify_func(unit_test_path):
    """
    Dynamically load the verification function from a CR's unit_test.py file.
    """
    spec = importlib.util.spec_from_file_location("verify", unit_test_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Assume only one verify function is defined (e.g., cr1_verify_func)
    verify_func = [getattr(module, f) for f in dir(module) if f.endswith("_verify_func")][0]
    return verify_func


def run_model(model_path):
    """
    Execute a Python model file from its containing directory and return JSON output.
    """
    print(f"Running model: {model_path}")
    model_dir = os.path.dirname(model_path)
    model_file = os.path.basename(model_path)

    result = subprocess.run(
        [sys.executable, model_file],
        cwd=model_dir,  # run inside CR folder
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Model execution failed:\n{result.stderr}")

    try:
        output = json.loads(result.stdout)
        print("Model executed successfully.")
        return output
    except json.JSONDecodeError:
        raise ValueError(f"Model output is not valid JSON:\n{result.stdout}")


def generate_and_run_model(problem_path, cr_name, max_attempts=3):
    last_error = None
    last_code = None
    model_path = None

    for attempt in range(1, max_attempts + 1):
        print(f"Generating model (attempt {attempt}/{max_attempts})...")
        model_path, last_code = generate_model(
            problem_path,
            cr_name,
            error_message=last_error,
            previous_code=last_code,
            attempt=attempt,
        )
        try:
            model_output = run_model(model_path)
            return model_path, model_output, attempt
        except Exception as e:
            last_error = str(e)
            print(f"Generated model failed to run: {e}")

    raise GenerationFailed(max_attempts, last_error)


def run_pipeline(problem_path, cr_name, model_filename="reference_model.py", max_attempts=3):
    """
    Runs a ModRef CR end-to-end:
    1. Executes the model (e.g., reference_model.py or generated_model.py)
    2. Loads the CR's input_data.json
    3. Runs the unit test for that CR
    4. Saves and prints results
    """
    cr_path = os.path.join(problem_path, cr_name)
    print(f"\n=== Running pipeline for {cr_name} ===")

    problem = os.path.basename(problem_path)

    input_path = os.path.join(cr_path, "input_data.json")
    unit_test_path = os.path.join(cr_path, "unit_test.py")

    # Step 1: Run model
    try:
        if model_filename == "reference_model.py":
            model_path = os.path.join(cr_path, "reference_model.py")
            model_output = run_model(model_path)
            attempts = 1
        elif model_filename == "generated_model.py":
            model_path, model_output, attempts = generate_and_run_model(
                problem_path,
                cr_name,
                max_attempts=max_attempts,
            )
        else:
            raise ValueError("Unsupported model filename.")
    except Exception as e:
        print(f"Model failed to run {e}, Saving result...")
        attempts = getattr(e, "attempts", 1)
        error_message = getattr(e, "last_error", str(e))

        os.makedirs("results", exist_ok=True)
        out_file = f"results/{problem}_{cr_name}_run_{datetime.date.today()}.json"

        fail_payload = {
            "cr": cr_name,
            "model": model_filename,
            "timestamp": str(datetime.datetime.now()),
            "model_failed": True,
            "attempts": attempts,
            "error": error_message,
            "output": None,
            "result": "failed to run"
        }

        with open(out_file, "w") as f:
            json.dump(fail_payload, f, indent=2)

        print(f"Saved failure result to {out_file}")
        return 


    # Step 2: Load input data
    with open(input_path) as f:
        input_data = json.load(f)

    # Step 3: Run verification
    verify_func = load_verify_func(unit_test_path)
    result = verify_func(input_data, model_output)

    # Step 4: Save and display
    os.makedirs("results", exist_ok=True)
    out_file = f"results/{problem}_{cr_name}_run_{datetime.date.today()}.json"
    with open(out_file, "w") as f:
        json.dump({
            "cr": cr_name,
            "model": model_filename,
            "timestamp": str(datetime.datetime.now()),
            "attempts": attempts,
            "result": result,
            "output": model_output
        }, f, indent=2)

    print(f"Verification result for {cr_name}: {result}")
    print(f"Saved to {out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ModRef pipeline for a given problem and CR.")
    parser.add_argument("--problem", required=True, help="Path to the problem folder (e.g., problems/problem1)")
    parser.add_argument("--cr", required=True, help="Name of the CR folder (e.g., CR3)")
    parser.add_argument("--model", default="reference_model.py", help="Model filename to run (default: reference_model.py)")
    parser.add_argument("--mode", choices=["ref", "llm"], default="ref",
                    help="Generate and run LLM model or use reference model.")
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Max LLM generation attempts when a generated model fails to run.",
    )

    args = parser.parse_args()

    # Decide which model to run
    if args.mode == "ref":
        model_to_run = "reference_model.py"
    else:
        model_to_run = "generated_model.py"

    run_pipeline(
        args.problem,
        args.cr,
        model_filename=model_to_run,
        max_attempts=args.max_attempts,
    )
