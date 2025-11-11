import json, subprocess, sys

# Run reference model
ref = subprocess.run([sys.executable, "reference_model.py"],
                     capture_output=True, text=True)
ref_out = json.loads(ref.stdout)
ref_seq = ref_out["sequence"]

# Run generated model
gen = subprocess.run([sys.executable, "generated_model.py"],
                     capture_output=True, text=True)
gen_out = json.loads(gen.stdout)
gen_seq = gen_out["sequence"]

# Check output structure
assert "sequence" in gen_out, "Missing 'sequence' key"

# Load shared input data
with open("input_data.json") as f:
    data = json.load(f)
gap = data["gap_limit"]
n_types = len(data["demand"])

# Check both outputs satisfy spacing constraint
def check_spacing(seq, name):
    for t in range(n_types):
        for i in range(len(seq) - gap):
            window = seq[i:i + gap]
            assert t in window, f"{name} violates spacing for type {t} in window {i}-{i+gap}"

check_spacing(ref_seq, "reference model")
check_spacing(gen_seq, "generated model")

# Check equivalence (length, type coverage)
assert len(ref_seq) == len(gen_seq), "Sequence lengths differ"
assert set(ref_seq) == set(gen_seq), "Different car type sets"
print("CR2 passed: Both models satisfy spacing constraint and produce equivalent outputs.")