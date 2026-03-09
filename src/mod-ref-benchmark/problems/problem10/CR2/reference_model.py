from cpmpy import *
import json


def build_model(
    n_nurses,
    min_patients_per_nurse,
    max_patients_per_nurse,
    max_workload_per_nurse,
    patient_acuity,
    patient_zone,
    zone_distance
):
    n_patients = len(patient_acuity)

    if len(patient_zone) != n_patients:
        raise ValueError("patient_acuity and patient_zone must have equal length")

    n_zones = len(zone_distance)
    if n_zones == 0:
        raise ValueError("zone_distance must be non-empty")
    for z in range(n_zones):
        if len(zone_distance[z]) != n_zones:
            raise ValueError("zone_distance must be a square matrix")
    for i, z in enumerate(patient_zone):
        if not (0 <= z < n_zones):
            raise ValueError(f"patient_zone[{i}]={z} is out of range [0, {n_zones-1}]")

    # p[i] = nurse assigned to patient i
    p = intvar(0, n_nurses - 1, shape=n_patients, name="p")

    # workload per nurse
    w = intvar(0, max_workload_per_nurse, shape=n_nurses, name="w")

    total_workload = intvar(0, sum(patient_acuity), name="total_workload")
    max_dist = max(max(row) for row in zone_distance)
    n_pairs = n_patients * (n_patients - 1) // 2
    total_travel_cost = intvar(0, n_pairs * max_dist, name="total_travel_cost")

    model = Model()

    # Patient count constraints
    for k in range(n_nurses):
        cnt_k = sum(p[i] == k for i in range(n_patients))
        model += min_patients_per_nurse <= cnt_k
        model += cnt_k <= max_patients_per_nurse

    # CR2: one-zone-per-nurse restriction removed

    # Workload calculation
    for k in range(n_nurses):
        model += w[k] == sum(
            patient_acuity[i] * (p[i] == k)
            for i in range(n_patients)
        )
        model += w[k] <= max_workload_per_nurse

    model += total_workload == sum(w[k] for k in range(n_nurses))

    # Travel cost: patient pairs assigned to same nurse contribute zone distance
    model += total_travel_cost == sum(
        zone_distance[patient_zone[i]][patient_zone[j]] * (p[i] == p[j])
        for i in range(n_patients)
        for j in range(i + 1, n_patients)
    )

    # CR2 objective: minimize both workload and travel cost
    model.minimize(total_workload + total_travel_cost)

    return model, p, w, total_workload, total_travel_cost


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, p, w, total_workload, total_travel_cost = build_model(
        data["n_nurses"],
        data["min_patients_per_nurse"],
        data["max_patients_per_nurse"],
        data["max_workload_per_nurse"],
        data["patient_acuity"],
        data["patient_zone"],
        data["zone_distance"]
    )

    solution = {}
    if model.solve():
        solution["patient_assignment"] = p.value().tolist()
        solution["workload"] = w.value().tolist()
        solution["total_workload"] = int(total_workload.value())
        solution["total_travel_cost"] = int(total_travel_cost.value())

    print(json.dumps(solution))
