from cpmpy import *
import json


def build_model(horizon, capacities, jobs, deadlines):
    n_jobs = len(jobs)
    n_resources = len(capacities)

    if len(deadlines) != n_jobs:
        raise ValueError("deadlines must have one entry per job")

    s = intvar(0, horizon, shape=n_jobs, name="s")

    max_duration = max(duration for duration, _, _ in jobs)
    tardiness = intvar(0, horizon + max_duration, shape=n_jobs, name="tardiness")
    total_tardiness_ub = sum(
        max(0, horizon + jobs[i][0] - deadlines[i])
        for i in range(1, n_jobs - 1)
    )
    total_tardiness = intvar(0, total_tardiness_ub, name="total_tardiness")

    model = Model()

    # 1) Precedence constraints
    for i, (duration, successors, _) in enumerate(jobs):
        for j in successors:
            model += s[i] + duration <= s[j]

    # 2) Resource constraints
    for r in range(n_resources):
        starts = []
        durations = []
        ends = []
        demands = []

        for i, (duration, _, job_demands) in enumerate(jobs):
            if job_demands[r] > 0:
                starts.append(s[i])
                durations.append(duration)
                ends.append(s[i] + duration)
                demands.append(job_demands[r])

        if len(starts) > 0:
            model += Cumulative(
                start=starts,
                duration=durations,
                end=ends,
                demand=demands,
                capacity=capacities[r]
            )

    # 3) Tardiness definition: max(completion - deadline, 0)
    for i, (duration, _, _) in enumerate(jobs):
        completion_i = s[i] + duration
        model += tardiness[i] >= completion_i - deadlines[i]

    # Exclude dummy source/sink jobs from tardiness objective
    model += total_tardiness == sum(tardiness[i] for i in range(1, n_jobs - 1))

    # Objective: minimize total tardiness
    model.minimize(total_tardiness)

    return model, s, total_tardiness


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, s, total_tardiness = build_model(
        data["horizon"],
        data["capacities"],
        data["jobs"],
        data["deadlines"]
    )

    if model.solve():
        solution = {
            "start_times": s.value().tolist(),
            "total_tardiness": int(total_tardiness.value())
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
