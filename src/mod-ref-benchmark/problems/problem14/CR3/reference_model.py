from cpmpy import *
import json


def build_model(
    num_cargos,
    num_tanks,
    capacities,
    neighbours,
    impossible_cargos,
    volume_to_ship,
    incompatibilities,
    splittable_tanks,
    divider_loss,
):
    """
    Tank Allocation Problem - CR3

    CR3: selected tanks may optionally split into two subcompartments.
    Each tank has two cargo slots, but the second slot may be used only when the
    tank is split. A split tank loses `divider_loss` units of usable capacity.
    """

    if len(capacities) != num_tanks:
        raise ValueError("capacities must have length num_tanks")
    if len(neighbours) != num_tanks:
        raise ValueError("neighbours must have length num_tanks")
    if len(impossible_cargos) != num_tanks:
        raise ValueError("impossible_cargos must have length num_tanks")
    if len(volume_to_ship) != num_cargos:
        raise ValueError("volume_to_ship must have length num_cargos")
    if divider_loss < 0:
        raise ValueError("divider_loss must be non-negative")

    split_allowed = set(splittable_tanks)
    if len(split_allowed) != len(splittable_tanks):
        raise ValueError("splittable_tanks must not contain duplicates")
    for t in split_allowed:
        if not (0 <= t < num_tanks):
            raise ValueError(f"splittable_tanks contains invalid tank index {t}")
        if divider_loss >= capacities[t]:
            raise ValueError(
                f"divider_loss must be smaller than the capacity of splittable tank {t}"
            )

    for t, nbs in enumerate(neighbours):
        for nb in nbs:
            if not (0 <= nb < num_tanks):
                raise ValueError(f"neighbours[{t}] contains invalid tank index {nb}")
            if nb == t:
                raise ValueError(f"neighbours[{t}] may not contain tank {t} itself")

    for t, forbidden in enumerate(impossible_cargos):
        for c in forbidden:
            if not (1 <= c <= num_cargos):
                raise ValueError(f"impossible_cargos[{t}] contains invalid cargo id {c}")

    for pair in incompatibilities:
        if len(pair) != 2:
            raise ValueError("each incompatibility must contain exactly two cargo ids")
        c1, c2 = pair
        if not (1 <= c1 <= num_cargos and 1 <= c2 <= num_cargos):
            raise ValueError("incompatibility cargo ids must be between 1 and num_cargos")
        if c1 == c2:
            raise ValueError("incompatibility pairs must contain two distinct cargo ids")

    # CR3: two cargo/load slots per tank plus a split decision.
    cargo_in_tank = intvar(0, num_cargos, shape=(num_tanks, 2), name="cargo_in_tank")
    load = intvar(0, max(capacities), shape=(num_tanks, 2), name="load")
    split_tank = boolvar(shape=num_tanks, name="split_tank")
    unused_capacity = intvar(0, sum(capacities), name="unused_capacity")

    model = Model()

    # ------------------------------------------------
    # 1. CR3: slot usage and tank capacity consistency
    # ------------------------------------------------
    for t in range(num_tanks):
        if t not in split_allowed:
            model += ~split_tank[t]

        for s in range(2):
            model += load[t, s] <= capacities[t]
            model += (cargo_in_tank[t, s] == 0).implies(load[t, s] == 0)
            model += (cargo_in_tank[t, s] != 0).implies(load[t, s] >= 1)

        model += split_tank[t].implies(cargo_in_tank[t, 0] != 0)
        model += (cargo_in_tank[t, 1] != 0).implies(split_tank[t])
        model += (~split_tank[t]).implies(cargo_in_tank[t, 1] == 0)
        model += (~split_tank[t]).implies(load[t, 1] == 0)

        model += split_tank[t].implies(load[t, 0] + load[t, 1] <= capacities[t] - divider_loss)
        model += (~split_tank[t]).implies(load[t, 0] + load[t, 1] <= capacities[t])

        # If both slots are used, they represent two different cargoes in a fixed order.
        model += (cargo_in_tank[t, 1] != 0).implies(cargo_in_tank[t, 0] != 0)
        model += (cargo_in_tank[t, 1] != 0).implies(cargo_in_tank[t, 0] < cargo_in_tank[t, 1])

    # ------------------------------------------------
    # 2. Each cargo volume must be shipped exactly
    # ------------------------------------------------
    for c in range(1, num_cargos + 1):
        model += sum(
            load[t, s] * (cargo_in_tank[t, s] == c)
            for t in range(num_tanks)
            for s in range(2)
        ) == volume_to_ship[c - 1]

    # ------------------------------------------------
    # 3. Respect tank-specific forbidden cargos
    # ------------------------------------------------
    for t in range(num_tanks):
        for c in impossible_cargos[t]:
            for s in range(2):
                model += cargo_in_tank[t, s] != c

    # ------------------------------------------------
    # 4. Respect incompatibilities on neighbouring tanks
    # ------------------------------------------------
    incompatible_pairs = {tuple(sorted(pair)) for pair in incompatibilities}

    for t in range(num_tanks):
        for nb in neighbours[t]:
            if t < nb:
                for s1 in range(2):
                    for s2 in range(2):
                        for c1, c2 in incompatible_pairs:
                            model += ~(
                                ((cargo_in_tank[t, s1] == c1) & (cargo_in_tank[nb, s2] == c2))
                                |
                                ((cargo_in_tank[t, s1] == c2) & (cargo_in_tank[nb, s2] == c1))
                            )

    # ------------------------------------------------
    # 5. Objective: maximize total capacity of unused tanks
    # ------------------------------------------------
    model += unused_capacity == sum(
        capacities[t] * ((cargo_in_tank[t, 0] == 0) & (cargo_in_tank[t, 1] == 0))
        for t in range(num_tanks)
    )
    model.maximize(unused_capacity)

    return model, split_tank, cargo_in_tank, load, unused_capacity


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, split_tank, cargo_in_tank, load, unused_capacity = build_model(
        data["num_cargos"],
        data["num_tanks"],
        data["capacities"],
        data["neighbours"],
        data["impossible_cargos"],
        data["volume_to_ship"],
        data["incompatibilities"],
        data["splittable_tanks"],
        data["divider_loss"],
    )

    if model.solve(time_limit=10):
        solution = {
            "split_tank": [int(v) for v in split_tank.value().tolist()],
            "cargo_in_tank": cargo_in_tank.value().tolist(),
            "load": load.value().tolist(),
            "unused_capacity": int(unused_capacity.value()),
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
