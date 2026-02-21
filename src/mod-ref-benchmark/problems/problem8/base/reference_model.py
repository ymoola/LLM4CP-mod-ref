from cpmpy import *


def build_model(horizon, capacities, jobs):
    n_jobs = len(jobs)
    n_resources = len(capacities)

    s = intvar(0, horizon, shape=n_jobs, name="s")

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

    model.minimize(s[-1])

    return model, s

