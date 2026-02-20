from cpmpy import *
from itertools import combinations
import json


def build_model(n_groups, n_per_group, n_rounds):
    """
    Social Golfers CR2 feasibility model.

    Requirement change:
    Every pair of golfers must play together at least twice.
    """
    n_players = n_groups * n_per_group

    # g[r, p] = group id of player p in round r
    g = intvar(0, n_groups - 1, shape=(n_rounds, n_players), name="g")

    model = Model()

    # 1) Each group has exactly n_per_group golfers per round
    for r in range(n_rounds):
        for grp in range(n_groups):
            model += sum(g[r, p] == grp for p in range(n_players)) == n_per_group

    # 2) CR2: every pair must meet at least twice
    for p1, p2 in combinations(range(n_players), 2):
        model += sum(g[r, p1] == g[r, p2] for r in range(n_rounds)) >= 2

    return model, g


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, g = build_model(
        data["n_groups"],
        data["n_per_group"],
        data["n_rounds"]
    )

    if model.solve():
        print(json.dumps({
            "schedule": g.value().tolist()
        }))
    else:
        print("No solution found... UNSAT")
