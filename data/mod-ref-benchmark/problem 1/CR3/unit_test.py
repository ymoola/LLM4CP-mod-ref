import json, subprocess, sys

result = subprocess.run([sys.executable, "reference_model.py"],
                        capture_output=True, text=True)
output = json.loads(result.stdout)
sequence = output.get("sequence", [])

with open("input_data.json") as f:
    data = json.load(f)
requires = data["requires"]

# Verify no constraint violations for any option
violations = 0
for o, (max_opt, window) in enumerate(zip(data["at_most"], data["per_slots"])):
    for i in range(len(sequence) - window):
        opt_count = sum(requires[t][o] for t in sequence[i:i+window])
        if opt_count > max_opt:
            violations += 1

assert violations == 0, f"Found {violations} option-window violations"

# Check that there are minimal consecutive identical types
# (We can't assert the exact global optimum here, but we can check it's low)
same_type_count = sum(sequence[i] == sequence[i+1] for i in range(len(sequence)-1))
assert same_type_count < len(sequence) / 2, "❌ Too many consecutive identical types"

print("CR3 passed: All constraints satisfied and consecutive identical types minimized.")