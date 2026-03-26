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
    discharge_order,
    accessibility_pairs,
):
    """
    Tank Allocation Problem - CR2

    cargo_in_tank[t] = 0 means tank t is unused
    cargo_in_tank[t] = c means tank t is assigned to cargo c
    load[t] = actual volume loaded in tank t

    CR2: discharge-order accessibility rules constrain ordered tank pairs.
    """

    if len(capacities) != num_tanks:
        raise ValueError("capacities must have length num_tanks")
    if len(neighbours) != num_tanks:
        raise ValueError("neighbours must have length num_tanks")
    if len(impossible_cargos) != num_tanks:
        raise ValueError("impossible_cargos must have length num_tanks")
    if len(volume_to_ship) != num_cargos:
        raise ValueError("volume_to_ship must have length num_cargos")
    if len(discharge_order) != num_cargos:
        raise ValueError("discharge_order must have length num_cargos")
    if not accessibility_pairs:
        raise ValueError("accessibility_pairs must be non-empty")

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

    for c, order in enumerate(discharge_order, start=1):
        if not isinstance(order, int) or order < 1:
            raise ValueError(f"discharge_order[{c - 1}] must be a positive integer")

    for pair in incompatibilities:
        if len(pair) != 2:
            raise ValueError("each incompatibility must contain exactly two cargo ids")
        c1, c2 = pair
        if not (1 <= c1 <= num_cargos and 1 <= c2 <= num_cargos):
            raise ValueError("incompatibility cargo ids must be between 1 and num_cargos")
        if c1 == c2:
            raise ValueError("incompatibility pairs must contain two distinct cargo ids")

    seen_pairs = set()
    for idx, pair in enumerate(accessibility_pairs):
        if len(pair) != 2:
            raise ValueError("each accessibility pair must contain exactly two tank indices")
        a, b = pair
        if not (0 <= a < num_tanks and 0 <= b < num_tanks):
            raise ValueError(f"accessibility_pairs[{idx}] contains invalid tank indices")
        if a == b:
            raise ValueError(f"accessibility_pairs[{idx}] may not repeat the same tank")
        if (a, b) in seen_pairs:
            raise ValueError(f"accessibility_pairs[{idx}] is duplicated")
        seen_pairs.add((a, b))

    # 0 means unused, 1..num_cargos are real cargo ids
    cargo_in_tank = intvar(0, num_cargos, shape=num_tanks, name="cargo_in_tank")
    load = intvar(0, max(capacities), shape=num_tanks, name="load")
    unused_capacity = intvar(0, sum(capacities), name="unused_capacity")

    model = Model()

    # ------------------------------------------------
    # 1. Tank capacity and usage consistency
    # ------------------------------------------------
    for t in range(num_tanks):
        model += load[t] <= capacities[t]
        model += (cargo_in_tank[t] == 0).implies(load[t] == 0)
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
                        ((cargo_in_tank[t] == c1) & (cargo_in_tank[nb] == c2))
                        |
                        ((cargo_in_tank[t] == c2) & (cargo_in_tank[nb] == c1))
                    )

    # ------------------------------------------------
    # 5. CR2: discharge-accessibility ordering
    # ------------------------------------------------
    for a, b in accessibility_pairs:
        for c_front in range(1, num_cargos + 1):
            for c_back in range(1, num_cargos + 1):
                if discharge_order[c_front - 1] > discharge_order[c_back - 1]:
                    model += ~(
                        (cargo_in_tank[a] == c_front)
                        &
                        (cargo_in_tank[b] == c_back)
                    )

    # ------------------------------------------------
    # 6. Objective: maximize total capacity of unused tanks
    # ------------------------------------------------
    model += unused_capacity == sum(
        capacities[t] * (cargo_in_tank[t] == 0)
        for t in range(num_tanks)
    )
    model.maximize(unused_capacity)

    return model, cargo_in_tank, load, unused_capacity


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, cargo_in_tank, load, unused_capacity = build_model(
        data["num_cargos"],
        data["num_tanks"],
        data["capacities"],
        data["neighbours"],
        data["impossible_cargos"],
        data["volume_to_ship"],
        data["incompatibilities"],
        data["discharge_order"],
        data["accessibility_pairs"],
    )

    if model.solve(time_limit=10):
        solution = {
            "cargo_in_tank": cargo_in_tank.value().tolist(),
            "load": load.value().tolist(),
            "unused_capacity": int(unused_capacity.value()),
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
