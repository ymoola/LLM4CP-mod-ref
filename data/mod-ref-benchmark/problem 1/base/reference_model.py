"""
Car Sequencing baseline model
---------------------------------------------------------------
"""

from cpmpy import *

# ------------------------------------------------------------------
# Parameter placeholders (structure only – numeric data loaded externally)
# ------------------------------------------------------------------
# at_most: list[int] – max number of cars with option o in per_slots[o] consecutive positions
# per_slots: list[int] – number of consecutive timeslots per option
# demand: list[int] – number of cars per type
# requires: list[list[int]] – binary matrix [n_types x n_options]
# ------------------------------------------------------------------
# Model structure
# ------------------------------------------------------------------

def build_model(at_most, per_slots, demand, requires):
    requires = cpm_array(requires)
    n_cars = sum(demand)
    n_options = len(at_most)
    n_types = len(demand)

    # Decision variables
    sequence = intvar(0, n_types - 1, shape=n_cars, name="sequence")
    setup = boolvar(shape=(n_cars, n_options), name="setup")

    # Model definition
    model = Model()

    # 1. Demand satisfaction
    model += [sum(sequence == t) == demand[t] for t in range(n_types)]

    # 2. Option consistency
    for s in range(n_cars):
        for o in range(n_options):
            model += (setup[s, o] == requires[sequence[s], o])

    # 3. Capacity per option (no more than at_most[o] cars per per_slots[o] window)
    for o in range(n_options):
        for s in range(n_cars - per_slots[o]):
            slot_range = range(s, s + per_slots[o])
            model += (sum(setup[slot_range, o]) <= at_most[o])

    return model, sequence