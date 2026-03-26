from cpmpy import *
import json


def build_model(
    num_cargos,
    num_tanks,
    capacities,
    neighbours,
    impossible_cargos,
    volume_to_ship,
    incompatibilities
):
    """
    Tank Allocation Problem

    cargo_in_tank[t] = 0 means tank t is unused
    cargo_in_tank[t] = c means tank t is assigned to cargo c
    load[t] = actual volume loaded in tank t
    """

    # 0 means unused, 1..num_cargos are real cargo ids
    cargo_in_tank = intvar(0, num_cargos, shape=num_tanks, name="cargo_in_tank")
    load = intvar(0, max(capacities), shape=num_tanks, name="load")
    unused_capacity = intvar(0, sum(capacities), name="unused_capacity")

    model = Model()

    # ------------------------------------------------
    # 1. Tank capacity and usage consistency
    # ------------------------------------------------
    for t in range(num_tanks):
        # load cannot exceed tank capacity
        model += load[t] <= capacities[t]

        # empty tank has zero load
        model += (cargo_in_tank[t] == 0).implies(load[t] == 0)

        # used tank must carry a positive load
        model += (cargo_in_tank[t] != 0).implies(load[t] >= 1)

    # ------------------------------------------------
    # 2. Each cargo volume must be shipped exactly
    # ------------------------------------------------
    for c in range(1, num_cargos + 1):
        model += sum(
            load[t] * (cargo_in_tank[t] == c)
            for t in range(num_tanks)
        ) == volume_to_ship[c - 1]

    # ------------------------------------------------
    # 3. Respect tank-specific forbidden cargos
    # ------------------------------------------------
    for t in range(num_tanks):
        for c in impossible_cargos[t]:
            model += cargo_in_tank[t] != c

    # ------------------------------------------------
    # 4. Respect incompatibilities on neighbouring tanks
    # ------------------------------------------------
    incompatible_pairs = {tuple(sorted(pair)) for pair in incompatibilities}

    for t in range(num_tanks):
        for nb in neighbours[t]:
            if t < nb:
                for c1, c2 in incompatible_pairs:
                    model += ~(
                        ((cargo_in_tank[t] == c1) & (cargo_in_tank[nb] == c2)) |
                        ((cargo_in_tank[t] == c2) & (cargo_in_tank[nb] == c1))
                    )

    # ------------------------------------------------
    # 5. Objective: maximize total capacity of unused tanks
    # ------------------------------------------------
    model += unused_capacity == sum(
        capacities[t] * (cargo_in_tank[t] == 0)
        for t in range(num_tanks)
    )
    model.maximize(unused_capacity)

    return model, cargo_in_tank, load, unused_capacity

