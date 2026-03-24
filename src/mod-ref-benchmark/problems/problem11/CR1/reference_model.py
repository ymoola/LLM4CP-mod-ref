from cpmpy import *
import json


def build_model(n_days_per_week, n_weeks, s_min, s_max, requirements):
    """
    Rotating Rostering feasibility model - CR1.

    CR1: No employee may work more than 2 consecutive night shifts.
    The existing s_min / s_max rules remain unchanged for all other shifts.

    Shift encoding:
        0 = off
        1 = early
        2 = late
        3 = night
    """

    OFF, EARLY, LATE, NIGHT = 0, 1, 2, 3
    NIGHT_MAX = 2  # CR1: max consecutive night shifts
    n_shifts = 4
    n_days = n_days_per_week * n_weeks

    # x[d] = shift on flattened day d of the cyclic roster
    x = intvar(0, n_shifts - 1, shape=n_days, name="x")

    # y[w,d] = shift on day d of week w
    y = intvar(0, n_shifts - 1, shape=(n_weeks, n_days_per_week), name="y")

    model = Model()

    # ------------------------------------------------
    # 1. Link flattened and 2D representations
    # ------------------------------------------------
    for w in range(n_weeks):
        for d in range(n_days_per_week):
            model += y[w, d] == x[w * n_days_per_week + d]

    # ------------------------------------------------
    # 2. Weekend days must match
    # Saturday = 5, Sunday = 6
    # ------------------------------------------------
    SATURDAY, SUNDAY = 5, 6
    for w in range(n_weeks):
        model += y[w, SATURDAY] == y[w, SUNDAY]

    # ------------------------------------------------
    # 3. Minimum run length for each shift
    # If the shift changes, the new shift must continue
    # for at least s_min consecutive days
    # ------------------------------------------------
    for i in range(n_days):
        nxt = (i + 1) % n_days
        change = (x[i] != x[nxt])
        for t in range(1, s_min):
            model += change.implies(x[(nxt + t) % n_days] == x[nxt])

    # ------------------------------------------------
    # 4. Maximum run length for each shift
    # No shift may appear more than s_max days in a row
    # ------------------------------------------------
    for i in range(n_days):
        same_run = sum(x[(i + t) % n_days] == x[i] for t in range(1, s_max))
        model += (same_run == (s_max - 1)).implies(x[(i + s_max) % n_days] != x[i])

    # ------------------------------------------------
    # 5. At least 2 rest days in every 2-week window
    # ------------------------------------------------
    window_len = 2 * n_days_per_week
    for i in range(n_days):
        model += sum(x[(i + t) % n_days] == OFF for t in range(window_len)) >= 2

    # ------------------------------------------------
    # 6. Forward rotating shift order
    # After a shift, next day must be same shift,
    # a later shift, or a rest day
    # ------------------------------------------------
    for i in range(n_days):
        nxt = (i + 1) % n_days
        model += (x[nxt] == OFF) | (x[i] <= x[nxt])

    # ------------------------------------------------
    # 7. Shift requirements for each weekday
    # Across all weeks, each weekday must have the
    # required number of employees for each shift
    # ------------------------------------------------
    for d in range(n_days_per_week):
        for s in range(n_shifts):
            model += sum(y[w, d] == s for w in range(n_weeks)) == requirements[d][s]

    # ------------------------------------------------
    # 8. CR1: Maximum 2 consecutive night shifts
    # For every cyclic window of NIGHT_MAX+1 days,
    # not all days may be night shifts
    # ------------------------------------------------
    for i in range(n_days):
        model += sum(
            x[(i + t) % n_days] == NIGHT for t in range(NIGHT_MAX + 1)
        ) <= NIGHT_MAX

    return model, x, y


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, x, y = build_model(
        data["n_days_per_week"],
        data["n_weeks"],
        data["s_min"],
        data["s_max"],
        data["requirements"]
    )

    if model.solve():
        solution = {
            "x_roster": x.value().tolist(),
            "y_roster": y.value().tolist()
        }
        print(json.dumps(solution))
    else:
        print("No solution found")