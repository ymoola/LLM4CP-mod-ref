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
    Verify Social Golfers CR3:
    - Base constraints: valid round assignments and exact group sizes
    - CR3 constraint: each golfer meets at least k_min_distinct distinct partners
    """
    n_groups = data_dict["n_groups"]
    n_per_group = data_dict["n_per_group"]
    n_rounds = data_dict["n_rounds"]
    k_min_distinct = data_dict["k_min_distinct"]

    n_players = n_groups * n_per_group

    assert isinstance(k_min_distinct, int), "k_min_distinct must be an int."
    assert 0 <= k_min_distinct <= n_players - 1, (
        f"k_min_distinct must be in [0, {n_players - 1}], got {k_min_distinct}."
    )

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

    # 3) CR3: each golfer meets enough distinct partners
    for p in range(n_players):
        distinct_partners = set()
        for q in range(n_players):
            if p == q:
                continue
            met = any(schedule0[r][p] == schedule0[r][q] for r in range(n_rounds))
            if met:
                distinct_partners.add(q)

        assert len(distinct_partners) >= k_min_distinct, (
            f"CR3 violated: golfer {p} met {len(distinct_partners)} distinct partners, "
            f"expected at least {k_min_distinct}."
        )

    return "pass"
