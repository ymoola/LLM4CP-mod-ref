import json, subprocess, sys

# Run reference model
ref = subprocess.run([sys.executable, "reference_model.py"],
                     capture_output=True, text=True)
ref_out = json.loads(ref.stdout)

# Run generated model (assumed saved as generated_model.py)
gen = subprocess.run([sys.executable, "generated_model.py"],
                     capture_output=True, text=True)
gen_out = json.loads(gen.stdout)

# Check output structure
assert "sequence" in gen_out, "Missing 'sequence' key"
assert "total_violations" in gen_out, "Missing 'total_violations' key"

# Check equivalence
ref_viol = ref_out["total_violations"]
gen_viol = gen_out["total_violations"]

assert abs(ref_viol - gen_viol) == 1, (
    f"Violation count mismatch: reference={ref_viol}, generated={gen_viol}"
)

print(f"CR3 test passed. Reference={ref_viol}, Generated={gen_viol}")