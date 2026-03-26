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
def cr2_verify_func(data_dict, hypothesis_solution):
    num_cargos = data_dict["num_cargos"]
    num_tanks = data_dict["num_tanks"]
    capacities = data_dict["capacities"]
    neighbours = data_dict["neighbours"]
    impossible_cargos = data_dict["impossible_cargos"]
    volume_to_ship = data_dict["volume_to_ship"]
    incompatibilities = data_dict["incompatibilities"]
    discharge_order = data_dict["discharge_order"]
    accessibility_pairs = data_dict["accessibility_pairs"]
    ref_opt_val = data_dict.get("ref_opt_val", None)

    try:
        cargo_in_tank = hypothesis_solution["cargo_in_tank"]
        load = hypothesis_solution["load"]
        unused_capacity = hypothesis_solution["unused_capacity"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    assert isinstance(cargo_in_tank, list), "cargo_in_tank must be a list"
    assert isinstance(load, list), "load must be a list"
    assert len(cargo_in_tank) == num_tanks, (
        f"cargo_in_tank must have length {num_tanks}, got {len(cargo_in_tank)}"
    )
    assert len(load) == num_tanks, (
        f"load must have length {num_tanks}, got {len(load)}"
    )
    assert isinstance(unused_capacity, int), "unused_capacity must be an int"
    assert unused_capacity >= 0, "unused_capacity must be non-negative"

    max_capacity = max(capacities)
    for t in range(num_tanks):
        assert isinstance(cargo_in_tank[t], int), f"cargo_in_tank[{t}] must be an int"
        assert 0 <= cargo_in_tank[t] <= num_cargos, (
            f"cargo_in_tank[{t}]={cargo_in_tank[t]} out of range [0, {num_cargos}]"
        )
        assert isinstance(load[t], int), f"load[{t}] must be an int"
        assert 0 <= load[t] <= max_capacity, (
            f"load[{t}]={load[t]} out of range [0, {max_capacity}]"
        )

    # 1) Base tank capacity and usage consistency
    for t in range(num_tanks):
        assert load[t] <= capacities[t], (
            f"Tank {t} exceeds capacity: load {load[t]} > capacity {capacities[t]}."
        )
        if cargo_in_tank[t] == 0:
            assert load[t] == 0, f"Unused tank {t} must have zero load."
        else:
            assert load[t] >= 1, f"Used tank {t} must have positive load."

    # 2) Base exact shipped volume per cargo
    for c in range(1, num_cargos + 1):
        shipped = sum(load[t] for t in range(num_tanks) if cargo_in_tank[t] == c)
        assert shipped == volume_to_ship[c - 1], (
            f"Cargo {c} ships volume {shipped}, expected {volume_to_ship[c - 1]}."
        )

    # 3) Base forbidden cargo-tank assignments
    for t in range(num_tanks):
        assert cargo_in_tank[t] not in impossible_cargos[t], (
            f"Tank {t} may not carry cargo {cargo_in_tank[t]}."
        )

    # 4) Base neighbouring incompatibilities
    incompatible_pairs = {tuple(sorted(pair)) for pair in incompatibilities}
    for t in range(num_tanks):
        for nb in neighbours[t]:
            if t < nb:
                c1 = cargo_in_tank[t]
                c2 = cargo_in_tank[nb]
                if c1 != 0 and c2 != 0:
                    assert tuple(sorted((c1, c2))) not in incompatible_pairs, (
                        f"Neighbouring tanks {t} and {nb} carry incompatible cargos {c1} and {c2}."
                    )

    # 5) CR2 discharge-accessibility ordering
    for idx, pair in enumerate(accessibility_pairs):
        a, b = pair
        c_front = cargo_in_tank[a]
        c_back = cargo_in_tank[b]
        if c_front != 0 and c_back != 0:
            front_order = discharge_order[c_front - 1]
            back_order = discharge_order[c_back - 1]
            assert front_order <= back_order, (
                f"Accessibility pair {idx} violated: tank {a} carries cargo {c_front} "
                f"for discharge order {front_order}, while tank {b} carries cargo {c_back} "
                f"for earlier order {back_order}."
            )

    # 6) Objective consistency
    recomputed_unused_capacity = sum(
        capacities[t] for t in range(num_tanks) if cargo_in_tank[t] == 0
    )
    assert unused_capacity == recomputed_unused_capacity, (
        f"unused_capacity={unused_capacity}, recomputed={recomputed_unused_capacity}."
    )

    # 7) Optional optimality tag
    sol_opt = "sat"
    if ref_opt_val is not None:
        assert isinstance(ref_opt_val, int), "ref_opt_val must be an int when provided"
        sol_opt = "optimal" if unused_capacity == ref_opt_val else "sat"

    return "pass", sol_opt
