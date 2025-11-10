import json, subprocess, sys

result = subprocess.run([sys.executable, "reference_model.py"],
                        capture_output=True, text=True)
output = json.loads(result.stdout)
sequence = output.get("sequence", [])

with open("input_data.json") as f:
    data = json.load(f)
requires = data["requires"]

violations = 0
for i in range(len(sequence)-3):
    ac_count = sum(requires[t][0] for t in sequence[i:i+4])
    if ac_count > 1:
        violations += 1

assert violations == 0, f"Found {violations} air-conditioning violations"
print("CR1 passed")