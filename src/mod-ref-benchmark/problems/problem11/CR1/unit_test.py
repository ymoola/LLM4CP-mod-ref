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
    Verify Rotating Rostering CR1:
    - Base constraints: link, weekend match, min/max run, rest days, forward order, requirements
    - CR1 constraint: no more than 2 consecutive night shifts
    """
    n_days_per_week = data_dict["n_days_per_week"]
    n_weeks = data_dict["n_weeks"]
    s_min = data_dict["s_min"]
    s_max = data_dict["s_max"]
    requirements = data_dict["requirements"]

    n_days = n_days_per_week * n_weeks
    n_shifts = 4
    OFF, EARLY, LATE, NIGHT = 0, 1, 2, 3
    NIGHT_MAX = 2
    SATURDAY, SUNDAY = 5, 6

    # 1) Extract solution
    try:
        x_roster = hypothesis_solution["x_roster"]
        y_roster = hypothesis_solution["y_roster"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    # 2) Type and shape checks
    assert isinstance(x_roster, list), "x_roster must be a list"
    assert len(x_roster) == n_days, (
        f"x_roster must have length {n_days}, got {len(x_roster)}"
    )
    for i, v in enumerate(x_roster):
        assert isinstance(v, int), f"x_roster[{i}] must be an int"
        assert 0 <= v <= 3, f"x_roster[{i}]={v} out of range [0, 3]"

    assert isinstance(y_roster, list), "y_roster must be a list"
    assert len(y_roster) == n_weeks, (
        f"y_roster must have {n_weeks} rows, got {len(y_roster)}"
    )
    for w in range(n_weeks):
        assert isinstance(y_roster[w], list), f"y_roster[{w}] must be a list"
        assert len(y_roster[w]) == n_days_per_week, (
            f"y_roster[{w}] must have length {n_days_per_week}, got {len(y_roster[w])}"
        )
        for d in range(n_days_per_week):
            v = y_roster[w][d]
            assert isinstance(v, int), f"y_roster[{w}][{d}] must be an int"
            assert 0 <= v <= 3, f"y_roster[{w}][{d}]={v} out of range [0, 3]"

    # 3) Constraint 1: link x and y
    for w in range(n_weeks):
        for d in range(n_days_per_week):
            flat = w * n_days_per_week + d
            assert x_roster[flat] == y_roster[w][d], (
                f"Link violated at week {w}, day {d}: "
                f"x_roster[{flat}]={x_roster[flat]} != y_roster[{w}][{d}]={y_roster[w][d]}"
            )

    # 4) Constraint 2: weekend days must match within each week
    for w in range(n_weeks):
        assert y_roster[w][SATURDAY] == y_roster[w][SUNDAY], (
            f"Weekend mismatch in week {w}: "
            f"Saturday={y_roster[w][SATURDAY]}, Sunday={y_roster[w][SUNDAY]}"
        )

    # 5) Constraint 3: minimum run length
    for i in range(n_days):
        nxt = (i + 1) % n_days
        if x_roster[i] != x_roster[nxt]:
            for t in range(1, s_min):
                pos = (nxt + t) % n_days
                assert x_roster[pos] == x_roster[nxt], (
                    f"Min run violated: shift changes at day {i}->{nxt}, "
                    f"but day {pos} has shift {x_roster[pos]} instead of {x_roster[nxt]}"
                )

    # 6) Constraint 4: maximum run length (general, all shifts)
    for i in range(n_days):
        run_len = sum(
            1 for t in range(1, s_max)
            if x_roster[(i + t) % n_days] == x_roster[i]
        )
        if run_len == s_max - 1:
            beyond = (i + s_max) % n_days
            assert x_roster[beyond] != x_roster[i], (
                f"Max run violated at day {i}: shift {x_roster[i]} runs "
                f"at least {s_max + 1} days (beyond day {beyond})"
            )

    # 7) Constraint 5: at least 2 rest days in every 2-week window
    window_len = 2 * n_days_per_week
    for i in range(n_days):
        rest_count = sum(
            1 for t in range(window_len)
            if x_roster[(i + t) % n_days] == OFF
        )
        assert rest_count >= 2, (
            f"Rest day constraint violated starting at day {i}: "
            f"only {rest_count} rest days in {window_len}-day window (need >= 2)"
        )

    # 8) Constraint 6: forward rotating shift order
    for i in range(n_days):
        nxt = (i + 1) % n_days
        assert x_roster[nxt] == OFF or x_roster[i] <= x_roster[nxt], (
            f"Forward order violated at day {i}->{nxt}: "
            f"shift {x_roster[i]} followed by shift {x_roster[nxt]}"
        )

    # 9) Constraint 7: shift requirements per weekday
    for d in range(n_days_per_week):
        for s in range(n_shifts):
            count = sum(1 for w in range(n_weeks) if y_roster[w][d] == s)
            assert count == requirements[d][s], (
                f"Requirement violated for weekday {d}, shift {s}: "
                f"got {count}, expected {requirements[d][s]}"
            )

    # 10) CR1: no more than NIGHT_MAX consecutive night shifts
    for i in range(n_days):
        night_run = sum(
            1 for t in range(NIGHT_MAX + 1)
            if x_roster[(i + t) % n_days] == NIGHT
        )
        assert night_run <= NIGHT_MAX, (
            f"CR1 violated: {NIGHT_MAX + 1} consecutive night shifts starting at day {i}"
        )

    return "pass", "sat"