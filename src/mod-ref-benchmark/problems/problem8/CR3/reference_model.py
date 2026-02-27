from cpmpy import *
import json


def build_model(horizon, capacities, jobs, unavailable_windows):
    n_jobs = len(jobs)
    n_resources = len(capacities)

    s = intvar(0, horizon, shape=n_jobs, name="s")

    model = Model()

    # 1) Base precedence constraints
    for i, (duration, successors, _) in enumerate(jobs):
        for j in successors:
            model += s[i] + duration <= s[j]

    # 2) Base resource-capacity constraints
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

    # 3) CR3 maintenance windows:
    # tasks using resource r cannot overlap any unavailable interval [w_start, w_end)
    for win in unavailable_windows:
        if not isinstance(win, list) or len(win) != 3:
            raise ValueError("Each unavailable_windows entry must be [resource, start, end]")

        r, w_start, w_end = win

        if not (isinstance(r, int) and isinstance(w_start, int) and isinstance(w_end, int)):
            raise ValueError("unavailable_windows entries must be integers [resource, start, end]")
        if not (0 <= r < n_resources):
            raise ValueError(f"Invalid resource index in unavailable window: {win}")
        if not (0 <= w_start < w_end <= horizon):
            raise ValueError(f"Invalid unavailable interval [start, end): {win}")

        for i, (duration, _, job_demands) in enumerate(jobs):
            if duration > 0 and job_demands[r] > 0:
                # Non-overlap with [w_start, w_end):
                # job i either ends before window starts or starts after window ends
                model += (s[i] + duration <= w_start) | (s[i] >= w_end)

    # Objective unchanged: minimize project completion time
    model.minimize(s[-1])

    return model, s


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, s = build_model(
        data["horizon"],
        data["capacities"],
        data["jobs"],
        data["unavailable_windows"]
    )

    if model.solve():
        solution = {
            "start_times": s.value().tolist()
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
