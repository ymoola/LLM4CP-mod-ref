from cpmpy import *
import json


def build_model(
    n_nurses,
    min_patients_per_nurse,
    max_patients_per_nurse,
    max_workload_per_nurse,
    patient_acuity,
    patient_zone
):

    n_patients = len(patient_acuity)

    # p[i] = nurse assigned to patient i
    p = intvar(0, n_nurses - 1, shape=n_patients, name="p")

    # workload of each nurse
    w = intvar(0, max_workload_per_nurse, shape=n_nurses, name="w")

    model = Model()

    # Patient count constraints

    for k in range(n_nurses):
        model += (
            min_patients_per_nurse
            <= sum(p[i] == k for i in range(n_patients))
        )
        model += (
            sum(p[i] == k for i in range(n_patients))
            <= max_patients_per_nurse
        )

    # Nurses can only serve one zone

    for i in range(n_patients):
        for j in range(i + 1, n_patients):
            if patient_zone[i] != patient_zone[j]:
                model += p[i] != p[j]


    # Workload calculation
    for k in range(n_nurses):
        model += w[k] == sum(
            patient_acuity[i] * (p[i] == k)
            for i in range(n_patients)
        )

        model += w[k] <= max_workload_per_nurse


    # Objective: balance workloads
    model.minimize(
        sum(w[k] * w[k] for k in range(n_nurses))
    )

    return model, p, w

