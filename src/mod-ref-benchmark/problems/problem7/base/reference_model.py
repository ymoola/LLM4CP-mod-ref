from cpmpy import *
from itertools import combinations


def build_model(n_groups, n_per_group, n_rounds):
    """
    Social Golfers feasibility model.

    Parameters:
        n_groups      : number of groups per round
        n_per_group   : size of each group
        n_rounds      : number of rounds

    Total players = n_groups * n_per_group
    """

    n_players = n_groups * n_per_group

    # g[r, p] = group index of player p in round r
    g = intvar(0, n_groups - 1, shape=(n_rounds, n_players), name="g")

    model = Model()

    # ----------------------------------
    # 1. Each group has correct size
    # ----------------------------------
    for r in range(n_rounds):
        for grp in range(n_groups):
            model += sum(g[r, p] == grp for p in range(n_players)) == n_per_group

    # ----------------------------------
    # 2. No pair meets more than once
    # ----------------------------------
    for p1, p2 in combinations(range(n_players), 2):
        for r1, r2 in combinations(range(n_rounds), 2):
            model += (g[r1, p1] != g[r1, p2]) | (g[r2, p1] != g[r2, p2])

    return model, g

