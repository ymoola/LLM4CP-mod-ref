from cpmpy import *
from itertools import combinations
import json



def build_model(n_groups, n_per_group, n_rounds):
    n_players = n_groups * n_per_group

    g = intvar(0, n_groups - 1, shape=(n_rounds, n_players), name="g")

    model = Model()

    # Group size constraints
    for r in range(n_rounds):
        for grp in range(n_groups):
            model += sum(g[r, p] == grp for p in range(n_players)) == n_per_group

    pairs = list(combinations(range(n_players), 2))
    n_pairs = len(pairs)

    meet = boolvar(shape=(n_rounds, n_pairs), name="meet")
    pair_count = intvar(0, n_rounds, shape=n_pairs, name="pair_count")
    repeats = intvar(0, n_rounds - 1, shape=n_pairs, name="repeats")
    has_meeting = boolvar(shape=n_pairs, name="has_meeting")

    for k, (p1, p2) in enumerate(pairs):
        for r in range(n_rounds):
            model += meet[r, k] == (g[r, p1] == g[r, p2])

        model += pair_count[k] == sum(meet[:, k])

        # Exact modeling of max(pair_count - 1, 0)
        model += has_meeting[k] == (pair_count[k] >= 1)
        model += repeats[k] == pair_count[k] - has_meeting[k]

    total_repeated_pairings = sum(repeats)
    model.minimize(total_repeated_pairings)

    return model, g, total_repeated_pairings


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, g, total_repeated_pairings = build_model(
        data["n_groups"],
        data["n_per_group"],
        data["n_rounds"]
    )

    if model.solve():
        print(json.dumps({
            "schedule": g.value().tolist(),
            "total_repeated_pairings": int(total_repeated_pairings.value())
        }))
    else:
        print("No solution found... UNSAT")
