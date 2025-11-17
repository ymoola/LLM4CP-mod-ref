import ollama
import json
import os


def generate_model(
    problem_path,
    cr_name,
    desc_filename="desc.json",
    base_desc_filename="problem_desc.txt",
    base_model_filename="reference_model.py",
    model_filename="generated_model.py"
):
    """
    Generates a CPMPy model that incorporates the change request (CR)
    using an Ollama LLM (qwen3-coder:30b).

    The LLM sees:
      1. Base natural-language description (base/problem_desc.txt)
      2. Base reference CPMPy model (base/reference_model.py)
      3. CR description + parameter info + expected output format (CR*/desc.json)

    It does NOT see input_data.json (values must NOT be leaked).
    The generated model must load input_data.json at runtime.
    """

  
    # Paths
    cr_path = os.path.join(problem_path, cr_name)
    base_path = os.path.join(problem_path, "base")

    desc_path = os.path.join(cr_path, desc_filename)
    base_desc_path = os.path.join(base_path, base_desc_filename)
    base_model_path = os.path.join(base_path, base_model_filename)

    # Load base natural description
    if not os.path.exists(base_desc_path):
        raise FileNotFoundError(f"Missing base problem description at: {base_desc_path}")

    with open(base_desc_path, "r") as f:
        base_nl_description = f.read()


    # Load base reference model
    if not os.path.exists(base_model_path):
        raise FileNotFoundError(f"Missing base reference model at: {base_model_path}")

    with open(base_model_path, "r") as f:
        base_model_code = f.read()

    # Load CR description (desc.json)
    with open(desc_path, "r") as f:
        cr_desc = json.load(f)

    cr_nl = cr_desc.get("content", "(No CR content provided)")
    value_info = cr_desc.get("value_info", [])
    ref_sol_format = cr_desc.get("ref_sol_format", {})

    # Build LLM prompt
    prompt = f"""
You are a CPMPy modeling assistant.

=== Base Problem Description (Natural Language) ===
{base_nl_description}

=== Base CPMPy Reference Model (Before Change Request) ===
{base_model_code}

=== Change Request (CR) Description ===
{cr_nl}

=== Parameter Description (value_info) ===
{json.dumps(value_info, indent=2)}

=== Expected Output Format (ref_sol_format) ===
{json.dumps(ref_sol_format, indent=2)}

=== Instructions ===
Your task is to generate a NEW CPMPy model implementing the change request (CR).

Requirements:
  1. Use the SAME parameter names and input structure described in value_info.
  2. Load ALL numeric parameter values from 'input_data.json' at runtime.
     (Do NOT hard-code any numbers into the model.)
  3. Modify the base model ONLY where required by the CR.
  4. Preserve original constraints unless overridden by the CR.
  5. Solve the model.
  6. Print a JSON dictionary exactly matching ref_sol_format.

Formatting rules:
  - Output ONLY valid Python CPMPy code.
  - Do NOT include markdown, python backticks, comments, or explanations.
  - The final line must be a print(json.dumps(...)).
IMPORTANT:
- Do NOT include any text before the Python code.
- DO NOT include ```python ``` just the code.
- Do NOT prefix with explanations, comments, markdown, or warnings.
- If you want to include comments, include only Python # comments.

Now generate the complete CPMPy script implementing the CR.
Output ONLY the complete CPMPy code. No additional text.
"""

    print(f"prompt: \n {prompt}")


    # Call LLM   
    print("Calling LLM to generate model...")

    response = ollama.generate(
        model="gpt-oss:20b",
        prompt=prompt,
    )

    print(f"response: \n {response}")

    code = response["response"]


    # Save generated model
    output_path = os.path.join(cr_path, model_filename)
    with open(output_path, "w") as f:
        f.write(code)

    print(f"Generated model saved to {output_path}")

    return output_path