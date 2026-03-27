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
def cr3_verify_func(data_dict, hypothesis_solution):
    num_cargos = data_dict["num_cargos"]
    num_tanks = data_dict["num_tanks"]
    capacities = data_dict["capacities"]
    neighbours = data_dict["neighbours"]
    impossible_cargos = data_dict["impossible_cargos"]
    volume_to_ship = data_dict["volume_to_ship"]
    incompatibilities = data_dict["incompatibilities"]
    splittable_tanks = set(data_dict["splittable_tanks"])
    divider_loss = data_dict["divider_loss"]
    ref_opt_val = data_dict.get("ref_opt_val", None)

    try:
        split_tank = hypothesis_solution["split_tank"]
        cargo_in_tank = hypothesis_solution["cargo_in_tank"]
        load = hypothesis_solution["load"]
        unused_capacity = hypothesis_solution["unused_capacity"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    assert isinstance(split_tank, list), "split_tank must be a list"
    assert len(split_tank) == num_tanks, (
        f"split_tank must have length {num_tanks}, got {len(split_tank)}"
    )
    assert isinstance(cargo_in_tank, list), "cargo_in_tank must be a list"
    assert len(cargo_in_tank) == num_tanks, (
        f"cargo_in_tank must have length {num_tanks}, got {len(cargo_in_tank)}"
    )
    assert isinstance(load, list), "load must be a list"
    assert len(load) == num_tanks, (
        f"load must have length {num_tanks}, got {len(load)}"
    )
    assert isinstance(unused_capacity, int), "unused_capacity must be an int"
    assert unused_capacity >= 0, "unused_capacity must be non-negative"

    max_capacity = max(capacities)
    for t in range(num_tanks):
        assert isinstance(split_tank[t], (bool, int)), f"split_tank[{t}] must be boolean/int"
        split_val = int(split_tank[t])
        assert split_val in (0, 1), f"split_tank[{t}] must be 0/1"

        assert isinstance(cargo_in_tank[t], list), f"cargo_in_tank[{t}] must be a list"
        assert len(cargo_in_tank[t]) == 2, f"cargo_in_tank[{t}] must have length 2"
        assert isinstance(load[t], list), f"load[{t}] must be a list"
        assert len(load[t]) == 2, f"load[{t}] must have length 2"

        for s in range(2):
            assert isinstance(cargo_in_tank[t][s], int), f"cargo_in_tank[{t}][{s}] must be an int"
            assert 0 <= cargo_in_tank[t][s] <= num_cargos, (
                f"cargo_in_tank[{t}][{s}]={cargo_in_tank[t][s]} out of range [0, {num_cargos}]"
            )
            assert isinstance(load[t][s], int), f"load[{t}][{s}] must be an int"
            assert 0 <= load[t][s] <= max_capacity, (
                f"load[{t}][{s}]={load[t][s]} out of range [0, {max_capacity}]"
            )

    # 1) CR3 slot usage and tank capacity consistency
    for t in range(num_tanks):
        split_val = int(split_tank[t])
        if t not in splittable_tanks:
            assert split_val == 0, f"Tank {t} may not be split."

        for s in range(2):
            assert load[t][s] <= capacities[t], (
                f"Tank {t} slot {s} exceeds capacity upper bound: {load[t][s]} > {capacities[t]}."
            )
            if cargo_in_tank[t][s] == 0:
                assert load[t][s] == 0, f"Unused slot {s} of tank {t} must have zero load."
            else:
                assert load[t][s] >= 1, f"Used slot {s} of tank {t} must have positive load."

        total_load = load[t][0] + load[t][1]
        if split_val == 1:
            assert cargo_in_tank[t][0] != 0, f"Split tank {t} must use its first slot."
            assert total_load <= capacities[t] - divider_loss, (
                f"Split tank {t} exceeds reduced capacity: {total_load} > {capacities[t] - divider_loss}."
            )
        else:
            assert cargo_in_tank[t][1] == 0, f"Unsplit tank {t} may not use its second slot."
            assert load[t][1] == 0, f"Unsplit tank {t} must have zero load in its second slot."
            assert total_load <= capacities[t], (
                f"Unsplit tank {t} exceeds capacity: {total_load} > {capacities[t]}."
            )

        if cargo_in_tank[t][1] != 0:
            assert split_val == 1, f"Tank {t} uses a second slot without being split."
            assert cargo_in_tank[t][0] != 0, f"Tank {t} cannot use slot 1 while slot 0 is empty."
            assert cargo_in_tank[t][0] < cargo_in_tank[t][1], (
                f"Tank {t} must store two different cargoes in increasing slot order."
            )

    # 2) Base exact shipped volume per cargo
    for c in range(1, num_cargos + 1):
        shipped = sum(
            load[t][s]
            for t in range(num_tanks)
            for s in range(2)
            if cargo_in_tank[t][s] == c
        )
        assert shipped == volume_to_ship[c - 1], (
            f"Cargo {c} ships volume {shipped}, expected {volume_to_ship[c - 1]}."
        )

    # 3) Base forbidden cargo-tank assignments
    for t in range(num_tanks):
        for s in range(2):
            assert cargo_in_tank[t][s] not in impossible_cargos[t], (
                f"Tank {t} may not carry cargo {cargo_in_tank[t][s]} in slot {s}."
            )

    # 4) Base neighbouring incompatibilities
    incompatible_pairs = {tuple(sorted(pair)) for pair in incompatibilities}
    for t in range(num_tanks):
        for nb in neighbours[t]:
            if t < nb:
                for s1 in range(2):
                    for s2 in range(2):
                        c1 = cargo_in_tank[t][s1]
                        c2 = cargo_in_tank[nb][s2]
                        if c1 != 0 and c2 != 0:
                            assert tuple(sorted((c1, c2))) not in incompatible_pairs, (
                                f"Neighbouring tanks {t} and {nb} carry incompatible cargos {c1} and {c2}."
                            )

    # 5) Objective consistency
    recomputed_unused_capacity = sum(
        capacities[t]
        for t in range(num_tanks)
        if cargo_in_tank[t][0] == 0 and cargo_in_tank[t][1] == 0
    )
    assert unused_capacity == recomputed_unused_capacity, (
        f"unused_capacity={unused_capacity}, recomputed={recomputed_unused_capacity}."
    )

    # 6) Optional optimality tag
    sol_opt = "sat"
    if ref_opt_val is not None:
        assert isinstance(ref_opt_val, int), "ref_opt_val must be an int when provided"
        sol_opt = "optimal" if unused_capacity == ref_opt_val else "sat"

    return "pass", sol_opt
