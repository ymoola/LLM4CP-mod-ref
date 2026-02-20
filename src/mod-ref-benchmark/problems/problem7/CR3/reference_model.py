from cpmpy import *
from itertools import combinations
import json



def build_model(n_groups, n_per_group, n_rounds, k_min_distinct):
    """
    Social Golfers CR3 feasibility model.

    Requirement change:
    Each golfer must play with at least k_min_distinct distinct other golfers.
    """
    n_players = n_groups * n_per_group

    if k_min_distinct < 0 or k_min_distinct > n_players - 1:
        raise ValueError("k_min_distinct must be between 0 and n_players-1")

    max_possible = n_rounds * (n_per_group - 1)
    if k_min_distinct > max_possible:
        raise ValueError("k_min_distinct too large for given rounds/group size")

    g = intvar(0, n_groups - 1, shape=(n_rounds, n_players), name="g")

    model = Model()

    # Group size constraints
    for r in range(n_rounds):
        for grp in range(n_groups):
            model += sum(g[r, p] == grp for p in range(n_players)) == n_per_group

    pairs = list(combinations(range(n_players), 2))
    met_pair = boolvar(shape=len(pairs), name="met_pair")

    for k, (p1, p2) in enumerate(pairs):
        meet = boolvar(shape=n_rounds)
        for r in range(n_rounds):
            model += meet[r] == (g[r, p1] == g[r, p2])
        model += met_pair[k] == (sum(meet) >= 1)

    # Fairness constraint
    for p in range(n_players):
        partner_bools = []
        for q in range(n_players):
            if p == q:
                continue
            idx = pairs.index((p, q) if p < q else (q, p))
            partner_bools.append(met_pair[idx])

        model += sum(partner_bools) >= k_min_distinct

    return model, g


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, g = build_model(
        data["n_groups"],
        data["n_per_group"],
        data["n_rounds"],
        data["k_min_distinct"]
    )

    if model.solve():
        print(json.dumps({
            "schedule": g.value().tolist()
        }))
    else:
        print("No solution found... UNSAT")
