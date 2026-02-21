from cpmpy import *
import json


def build_model(horizon, capacities, jobs, max_delays):
    n_jobs = len(jobs)
    n_resources = len(capacities)

    s = intvar(0, horizon, shape=n_jobs, name="s")

    model = Model()

    # Build successor lookup for validating constrained precedence arcs
    succ_sets = [set(successors) for _, successors, _ in jobs]

    # 1) Base precedence constraints
    for i, (duration, successors, _) in enumerate(jobs):
        for j in successors:
            model += s[i] + duration <= s[j]

    # 2) CR2 additional maximum-delay constraints on selected precedence arcs
    for arc in max_delays:
        if not isinstance(arc, list) or len(arc) != 3:
            raise ValueError("Each max_delays entry must be [pred, succ, max_delay]")

        i, j, dmax = arc

        if not (isinstance(i, int) and isinstance(j, int) and isinstance(dmax, int)):
            raise ValueError("max_delays entries must be integers [pred, succ, max_delay]")
        if not (0 <= i < n_jobs and 0 <= j < n_jobs):
            raise ValueError(f"Invalid job indices in max_delays entry: {arc}")
        if dmax < 0:
            raise ValueError(f"max_delay must be non-negative: {arc}")
        if j not in succ_sets[i]:
            raise ValueError(
                f"max_delays entry {arc} is invalid: ({i}->{j}) is not a precedence arc"
            )

        duration_i = jobs[i][0]
        # s[j] - (s[i] + duration_i) <= dmax
        model += s[j] <= s[i] + duration_i + dmax

    # 3) Resource constraints
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
        data["max_delays"]
    )

    if model.solve():
        solution = {
            "start_times": s.value().tolist()
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
