import traceback


def handle_assertions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AssertionError as e:
            return ("fail", str(e))
        except Exception as e:
            return {
                "err": repr(str(e)),
                "err_trace": repr(''.join(traceback.format_exception(None, e, e.__traceback__)))
            }
    return wrapper


@handle_assertions
def cr1_verify_func(data_dict, hypothesis_solution):
    """
    Verify RCPSP CR1:
    - Base constraints: precedence + renewable resource capacities
    - CR1 objective consistency: total tardiness (excluding dummy source/sink jobs)
    """
    horizon = data_dict["horizon"]
    capacities = data_dict["capacities"]
    jobs = data_dict["jobs"]
    deadlines = data_dict["deadlines"]
    ref_opt_val = data_dict.get("ref_opt_val", None)

    n_jobs = len(jobs)
    n_resources = len(capacities)

    try:
        start_times = hypothesis_solution["start_times"]
        total_tardiness = hypothesis_solution["total_tardiness"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    # 1) Basic format checks
    assert isinstance(start_times, list), "start_times must be a list"
    assert len(start_times) == n_jobs, (
        f"Error: Expected {n_jobs} start times, got {len(start_times)}."
    )
    assert isinstance(total_tardiness, int), "total_tardiness must be an int"
    assert total_tardiness >= 0, "total_tardiness must be non-negative"
    assert len(deadlines) == n_jobs, "deadlines length must equal number of jobs"

    for i, s in enumerate(start_times):
        assert isinstance(s, int), f"Error: start_times[{i}] must be an int."
        assert 0 <= s <= horizon, (
            f"Error: start_times[{i}]={s} is out of range [0, {horizon}]."
        )

    # 2) Job-data consistency + precedence constraints
    for i, job in enumerate(jobs):
        assert isinstance(job, list) and len(job) == 3, (
            f"Error: jobs[{i}] must have format [duration, successors, demands]."
        )
        duration, successors, demands = job

        assert isinstance(duration, int) and duration >= 0, (
            f"Error: jobs[{i}] has invalid duration {duration}."
        )
        assert isinstance(successors, list), f"Error: jobs[{i}].successors must be a list."
        assert isinstance(demands, list) and len(demands) == n_resources, (
            f"Error: jobs[{i}].demands must be a list of length {n_resources}."
        )
        for r, d in enumerate(demands):
            assert isinstance(d, int) and d >= 0, (
                f"Error: jobs[{i}].demands[{r}] must be a non-negative int."
            )

        for j in successors:
            assert isinstance(j, int) and 0 <= j < n_jobs, (
                f"Error: Invalid successor index {j} in jobs[{i}]."
            )
            assert start_times[i] + duration <= start_times[j], (
                f"Error: Precedence violated for arc {i}->{j}: "
                f"{start_times[i]} + {duration} > {start_times[j]}."
            )

    # 3) Renewable resource capacity constraints (discrete time check)
    end_time = max(start_times[i] + jobs[i][0] for i in range(n_jobs))
    for r in range(n_resources):
        cap = capacities[r]
        assert isinstance(cap, int) and cap >= 0, (
            f"Error: capacities[{r}] must be a non-negative int."
        )
        for t in range(end_time):
            usage = 0
            for i in range(n_jobs):
                s_i = start_times[i]
                dur_i = jobs[i][0]
                dem_i = jobs[i][2][r]
                if s_i <= t < s_i + dur_i:
                    usage += dem_i
            assert usage <= cap, (
                f"Error: Resource {r} exceeds capacity at time {t}: {usage} > {cap}."
            )

    # 4) CR1 objective consistency:
    # tardiness_i = max(start_i + duration_i - deadline_i, 0)
    # total tardiness excludes dummy source/sink: jobs 0 and n_jobs-1
    recomputed_tardiness = 0
    for i in range(1, n_jobs - 1):
        duration = jobs[i][0]
        completion = start_times[i] + duration
        recomputed_tardiness += max(completion - deadlines[i], 0)

    assert recomputed_tardiness == total_tardiness, (
        f"Error: reported total_tardiness={total_tardiness}, "
        f"recomputed={recomputed_tardiness}."
    )

    # 5) Optional optimality tag
    sol_opt = "sat"
    if ref_opt_val is not None:
        assert isinstance(ref_opt_val, int), "ref_opt_val must be an int when provided."
        sol_opt = "optimal" if total_tardiness == ref_opt_val else "sat"

    return "pass", sol_opt
