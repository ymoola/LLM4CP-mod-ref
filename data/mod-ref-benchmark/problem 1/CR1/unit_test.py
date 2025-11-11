import json, subprocess, sys

# Run reference model
ref = subprocess.run([sys.executable, "reference_model.py"],
                     capture_output=True, text=True)
ref_out = json.loads(ref.stdout)
ref_seq = ref_out["sequence"]

# Run generated model (assumed name)
gen = subprocess.run([sys.executable, "generated_model.py"],
                     capture_output=True, text=True)
gen_out = json.loads(gen.stdout)

# Check output structure
assert "sequence" in gen_out, "Missing 'sequence' key"
gen_seq = gen_out["sequence"]

# Check both outputs have the same structure
assert isinstance(ref_seq, list) and isinstance(gen_seq, list), "Invalid output structure"

# Verify no consecutive identical types in both
for seq_name, seq in [("reference", ref_seq), ("generated", gen_seq)]:
    for i in range(len(seq) - 1):
        assert seq[i] != seq[i + 1], f"{seq_name} has consecutive identical types at {i} and {i+1}"

# Verify structural equivalence between models
assert len(ref_seq) == len(gen_seq), "Sequence lengths differ"
assert set(ref_seq) == set(gen_seq), "Different car type sets"
print("CR1 passed: Both models satisfy 'no consecutive identical types' and produce equivalent sequences.")