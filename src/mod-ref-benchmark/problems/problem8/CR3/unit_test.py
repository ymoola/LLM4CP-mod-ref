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
def cr3_verify_func(data_dict, hypothesis_solution):
    """
    Verify RCPSP CR3:
    - Base constraints: precedence + renewable resource capacities
    - CR3 constraints: maintenance windows (no overlap for jobs using unavailable resource)
    - Objective consistency (optional): makespan = start_times[-1]
    """
    horizon = data_dict["horizon"]
    capacities = data_dict["capacities"]
    jobs = data_dict["jobs"]
    unavailable_windows = data_dict["unavailable_windows"]
    ref_opt_val = data_dict.get("ref_opt_val", None)

    n_jobs = len(jobs)
    n_resources = len(capacities)

    try:
        start_times = hypothesis_solution["start_times"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    # 1) Basic format checks
    assert isinstance(start_times, list), "start_times must be a list"
    assert len(start_times) == n_jobs, (
        f"Error: Expected {n_jobs} start times, got {len(start_times)}."
    )

    for i, s in enumerate(start_times):
        assert isinstance(s, int), f"Error: start_times[{i}] must be an int."
        assert 0 <= s <= horizon, (
            f"Error: start_times[{i}]={s} is out of range [0, {horizon}]."
        )

    # 2) Job-data consistency + base precedence constraints
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

    # 3) CR3 maintenance-window constraints
    for idx, win in enumerate(unavailable_windows):
        assert isinstance(win, list) and len(win) == 3, (
            f"Error: unavailable_windows[{idx}] must be [resource, start, end]."
        )
        r, w_start, w_end = win
        assert isinstance(r, int) and isinstance(w_start, int) and isinstance(w_end, int), (
            f"Error: unavailable_windows[{idx}] entries must be integers."
        )
        assert 0 <= r < n_resources, (
            f"Error: unavailable_windows[{idx}] has invalid resource index {r}."
        )
        assert 0 <= w_start < w_end <= horizon, (
            f"Error: unavailable_windows[{idx}] has invalid interval [{w_start}, {w_end})."
        )

        for i, (duration, _, demands) in enumerate(jobs):
            if duration > 0 and demands[r] > 0:
                no_overlap = (start_times[i] + duration <= w_start) or (start_times[i] >= w_end)
                assert no_overlap, (
                    f"Error: job {i} overlaps unavailable window [{w_start}, {w_end}) "
                    f"for resource {r}."
                )

    # 4) Renewable resource capacity constraints (discrete time check)
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

    # 5) objective in reference model is minimize s[-1]
    makespan = start_times[-1]
    sol_opt = "sat"
    if ref_opt_val is not None:
        assert isinstance(ref_opt_val, int), "ref_opt_val must be an int when provided."
        sol_opt = "optimal" if makespan == ref_opt_val else "sat"

    return "pass", sol_opt
