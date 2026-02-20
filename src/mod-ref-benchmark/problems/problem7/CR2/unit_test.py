import traceback
from itertools import combinations


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
def cr2_verify_func(data_dict, hypothesis_solution):
    """
    Verify Social Golfers CR2:
    - Base constraints: valid round assignments and exact group sizes
    - CR2 constraint: every pair of golfers plays together at least twice
    """
    n_groups = data_dict["n_groups"]
    n_per_group = data_dict["n_per_group"]
    n_rounds = data_dict["n_rounds"]

    n_players = n_groups * n_per_group

    try:
        schedule = hypothesis_solution["schedule"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    # 1) Format and range checks
    assert isinstance(schedule, list), "schedule must be a list"
    assert len(schedule) == n_rounds, (
        f"Error: Expected {n_rounds} rounds, got {len(schedule)}."
    )

    min_gid = None
    max_gid = None

    for r in range(n_rounds):
        row = schedule[r]
        assert isinstance(row, list), f"Error: schedule[{r}] must be a list."
        assert len(row) == n_players, (
            f"Error: Round {r} must assign {n_players} players, got {len(row)}."
        )
        for gid in row:
            assert isinstance(gid, int), "Error: Group ids must be integers."
            if min_gid is None or gid < min_gid:
                min_gid = gid
            if max_gid is None or gid > max_gid:
                max_gid = gid

    assert min_gid is not None and max_gid is not None, "Error: Empty schedule content."

    # Accept either 0-based or 1-based group IDs
    if min_gid >= 0 and max_gid <= n_groups - 1:
        schedule0 = schedule
    elif min_gid >= 1 and max_gid <= n_groups:
        schedule0 = [[gid - 1 for gid in row] for row in schedule]
    else:
        raise AssertionError(
            f"Error: Group ids out of range. Got [{min_gid}, {max_gid}], "
            f"expected 0..{n_groups - 1} or 1..{n_groups}."
        )


    # 2) Base constraints: exact group sizes
    for r in range(n_rounds):
        counts = [0] * n_groups
        for p in range(n_players):
            gid = schedule0[r][p]
            assert 0 <= gid < n_groups, (
                f"Error: Invalid group id at round {r}, player {p}: {gid}"
            )
            counts[gid] += 1

        for grp in range(n_groups):
            assert counts[grp] == n_per_group, (
                f"Error: Round {r}, group {grp} has size {counts[grp]}, "
                f"expected {n_per_group}."
            )

    # 3) CR2: every pair meets at least twice
    for p1, p2 in combinations(range(n_players), 2):
        meetings = sum(
            1 for r in range(n_rounds) if schedule0[r][p1] == schedule0[r][p2]
        )
        assert meetings >= 2, (
            f"CR2 violated: pair ({p1}, {p2}) meets {meetings} times, expected at least 2."
        )

    return "pass"
