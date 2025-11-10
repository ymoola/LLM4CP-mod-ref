import json, subprocess, sys

# Run model
result = subprocess.run([sys.executable, "reference_model.py"],
                        capture_output=True, text=True)
output = json.loads(result.stdout)
sequence = output.get("sequence", [])

with open("input_data.json") as f:
    data = json.load(f)
requires = data["requires"]
demand = data["demand"]

# Verify all car types appear the correct number of times
for t, expected in enumerate(demand):
    count = sequence.count(t)
    assert count == expected, f"❌ Type {t} appears {count} times, expected {expected}"

# Verify capacity constraint: no option exceeds its windowed maximum
violations = 0
for o, (max_opt, window) in enumerate(zip(data["at_most"], data["per_slots"])):
    for i in range(len(sequence) - window):
        opt_count = sum(requires[t][o] for t in sequence[i:i+window])
        if opt_count > max_opt:
            violations += 1

assert violations == 0, f"Found {violations} window violations"
print("CR2 passed: New car type (Type 5) added correctly and all constraints hold.")