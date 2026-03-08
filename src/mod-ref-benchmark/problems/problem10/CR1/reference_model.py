from cpmpy import *
import json


def build_model(
    n_nurses,
    min_patients_per_nurse,
    max_patients_per_nurse,
    max_workload_per_nurse,
    patient_type,
    patient_zone,
    workload_by_type_nurse
):
    n_patients = len(patient_type)

    if len(patient_zone) != n_patients:
        raise ValueError("patient_type and patient_zone must have equal length")

    n_types = len(workload_by_type_nurse)
    if n_types == 0:
        raise ValueError("workload_by_type_nurse must be non-empty")
    for t in range(n_types):
        if len(workload_by_type_nurse[t]) != n_nurses:
            raise ValueError("Each workload_by_type_nurse row must have length n_nurses")
    for i, t in enumerate(patient_type):
        if not (0 <= t < n_types):
            raise ValueError(f"patient_type[{i}]={t} is out of range [0, {n_types-1}]")

    # p[i] = nurse assigned to patient i
    p = intvar(0, n_nurses - 1, shape=n_patients, name="p")

    # workload of each nurse
    w = intvar(0, max_workload_per_nurse, shape=n_nurses, name="w")

    max_entry = max(max(row) for row in workload_by_type_nurse)
    total_workload_ub = min(
        n_patients * max_entry,
        n_nurses * max_workload_per_nurse
    )
    total_workload = intvar(0, total_workload_ub, name="total_workload")
    variance_numerator = intvar(
        0,
        n_nurses * n_nurses * max_workload_per_nurse * max_workload_per_nurse,
        name="variance_numerator"
    )

    model = Model()

    # Patient count constraints
    for k in range(n_nurses):
        cnt_k = sum(p[i] == k for i in range(n_patients))
        model += min_patients_per_nurse <= cnt_k
        model += cnt_k <= max_patients_per_nurse

    # Nurses can only serve one zone
    for i in range(n_patients):
        for j in range(i + 1, n_patients):
            if patient_zone[i] != patient_zone[j]:
                model += p[i] != p[j]

    # Type-dependent workload calculation
    for k in range(n_nurses):
        model += w[k] == sum(
            workload_by_type_nurse[patient_type[i]][k] * (p[i] == k)
            for i in range(n_patients)
        )
        model += w[k] <= max_workload_per_nurse

    model += total_workload == sum(w[k] for k in range(n_nurses))
    model += variance_numerator == (
        n_nurses * sum(w[k] * w[k] for k in range(n_nurses))
        - total_workload * total_workload
    )

    # CR1 objective: minimize both total workload and workload dispersion.
    # variance_numerator is equivalent to minimizing variance/std-dev, up to constants.
    model.minimize(total_workload + variance_numerator)

    return model, p, w, total_workload, variance_numerator


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, p, w, total_workload, variance_numerator = build_model(
        data["n_nurses"],
        data["min_patients_per_nurse"],
        data["max_patients_per_nurse"],
        data["max_workload_per_nurse"],
        data["patient_type"],
        data["patient_zone"],
        data["workload_by_type_nurse"]
    )

    solution = {}
    if model.solve():
        solution["patient_assignment"] = p.value().tolist()
        solution["workload"] = w.value().tolist()
        solution["total_workload"] = int(total_workload.value())
        solution["variance_numerator"] = int(variance_numerator.value())

    print(json.dumps(solution))
