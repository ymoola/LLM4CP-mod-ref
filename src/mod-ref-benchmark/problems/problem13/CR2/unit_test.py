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
    """
    Verify Bookshelf Design CR2:
    - Base cutting feasibility and height rule still apply
    - CR2 adds optional internal dividers, bay widths, and per-level per-bay shelves
    - Objective is total usable shelf space across all bays
    """
    thickness = data_dict["thickness"]
    cut_cost = data_dict["cut_cost"]
    vertical_gap = data_dict["vertical_gap"]
    lengths = data_dict["lengths"]
    max_bays = data_dict["max_bays"]
    ref_opt_val = data_dict.get("ref_opt_val", None)

    n_planks = len(lengths)
    max_len = max(lengths)
    max_shelves = max_len // (thickness + vertical_gap)
    max_verticals = max_bays + 1
    max_pieces = max_verticals + max_shelves * max_bays

    try:
        piece_lengths = hypothesis_solution["piece_lengths"]
        piece_from = hypothesis_solution["piece_from"]
        num_bays = hypothesis_solution["num_bays"]
        num_shelves = hypothesis_solution["num_shelves"]
        bay_widths = hypothesis_solution["bay_widths"]
        unit_height = hypothesis_solution["unit_height"]
        total_usable_shelf_space = hypothesis_solution["total_usable_shelf_space"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    # 1) Type and shape checks
    assert isinstance(piece_lengths, list), "piece_lengths must be a list"
    assert len(piece_lengths) == max_pieces, (
        f"piece_lengths must have length {max_pieces}, got {len(piece_lengths)}"
    )
    for i, val in enumerate(piece_lengths):
        assert isinstance(val, int), f"piece_lengths[{i}] must be an int"
        assert 0 <= val <= max_len, (
            f"piece_lengths[{i}]={val} out of range [0, {max_len}]"
        )

    assert isinstance(piece_from, list), "piece_from must be a list"
    assert len(piece_from) == max_pieces, (
        f"piece_from must have length {max_pieces}, got {len(piece_from)}"
    )
    for i, val in enumerate(piece_from):
        assert isinstance(val, int), f"piece_from[{i}] must be an int"
        assert 0 <= val < n_planks, (
            f"piece_from[{i}]={val} out of range [0, {n_planks - 1}]"
        )

    assert isinstance(num_bays, int), "num_bays must be an int"
    assert 1 <= num_bays <= max_bays, (
        f"num_bays={num_bays} out of range [1, {max_bays}]"
    )

    assert isinstance(num_shelves, int), "num_shelves must be an int"
    assert 1 <= num_shelves <= max_shelves, (
        f"num_shelves={num_shelves} out of range [1, {max_shelves}]"
    )

    assert isinstance(bay_widths, list), "bay_widths must be a list"
    assert len(bay_widths) == max_bays, (
        f"bay_widths must have length {max_bays}, got {len(bay_widths)}"
    )
    for b, val in enumerate(bay_widths):
        assert isinstance(val, int), f"bay_widths[{b}] must be an int"
        assert 0 <= val <= max_len, (
            f"bay_widths[{b}]={val} out of range [0, {max_len}]"
        )

    assert isinstance(unit_height, int), "unit_height must be an int"
    assert 0 <= unit_height <= max_len, (
        f"unit_height={unit_height} out of range [0, {max_len}]"
    )

    assert isinstance(total_usable_shelf_space, int), (
        "total_usable_shelf_space must be an int"
    )
    assert total_usable_shelf_space >= 0, "total_usable_shelf_space must be non-negative"

    # 2) CR2 structure: bay widths packed and positive exactly for used bays
    assert bay_widths[0] > 0, "The first bay must be used and have positive width."
    for b in range(max_bays - 1):
        assert bay_widths[b] >= bay_widths[b + 1], (
            f"bay_widths must be non-increasing, but bay_widths[{b}]={bay_widths[b]} "
            f"< bay_widths[{b + 1}]={bay_widths[b + 1]}."
        )

    recomputed_num_bays = sum(1 for width in bay_widths if width > 0)
    assert num_bays == recomputed_num_bays, (
        f"num_bays={num_bays}, recomputed from bay_widths={recomputed_num_bays}."
    )
    for b in range(num_bays, max_bays):
        assert bay_widths[b] == 0, (
            f"Unused bay slot {b} must have width 0, got {bay_widths[b]}."
        )

    # 3) Vertical panels and dividers
    used = [1 if val > 0 else 0 for val in piece_lengths]
    for v in range(max_verticals - 1):
        assert used[v] >= used[v + 1], (
            f"Vertical panel slots are not packed at indices {v} and {v + 1}."
        )

    assert used[0] == 1, "The left outer side panel must be used."
    assert used[1] == 1, "The right outer side panel must be used."

    recomputed_verticals = sum(used[v] for v in range(max_verticals))
    assert recomputed_verticals == num_bays + 1, (
        f"Expected {num_bays + 1} vertical panels, got {recomputed_verticals}."
    )

    for v in range(max_verticals):
        if v < num_bays + 1:
            assert piece_lengths[v] == unit_height, (
                f"Vertical panel slot {v} must have length {unit_height}, got {piece_lengths[v]}."
            )
        else:
            assert piece_lengths[v] == 0, (
                f"Unused vertical slot {v} must have length 0, got {piece_lengths[v]}."
            )

    # 4) Shelf piece layout across used levels and bays
    for s in range(max_shelves):
        for b in range(max_bays):
            idx = max_verticals + s * max_bays + b
            should_be_used = s < num_shelves and b < num_bays
            if should_be_used:
                assert piece_lengths[idx] == bay_widths[b], (
                    f"Shelf piece at level {s}, bay {b} must have length {bay_widths[b]}, "
                    f"got {piece_lengths[idx]}."
                )
            else:
                assert piece_lengths[idx] == 0, (
                    f"Unused shelf slot at level {s}, bay {b} must have length 0, got {piece_lengths[idx]}."
                )

    # 5) Height feasibility inherited from base
    assert unit_height >= num_shelves * (thickness + vertical_gap), (
        f"unit_height={unit_height} is too small for {num_shelves} shelf levels; "
        f"need at least {num_shelves * (thickness + vertical_gap)}."
    )

    # 6) Per-plank cutting feasibility inherited from base
    for p in range(n_planks):
        pieces_on_plank = [
            i for i in range(max_pieces) if piece_lengths[i] > 0 and piece_from[i] == p
        ]
        total_piece_length = sum(piece_lengths[i] for i in pieces_on_plank)
        cuts = max(0, len(pieces_on_plank) - 1)
        consumed_length = total_piece_length + cut_cost * cuts
        assert consumed_length <= lengths[p], (
            f"Plank {p} is overused: consumed {consumed_length}, available {lengths[p]}."
        )

    # 7) Objective consistency
    shelf_start = max_verticals
    recomputed_total_usable_shelf_space = sum(piece_lengths[i] for i in range(shelf_start, max_pieces))
    assert total_usable_shelf_space == recomputed_total_usable_shelf_space, (
        f"total_usable_shelf_space={total_usable_shelf_space}, "
        f"recomputed={recomputed_total_usable_shelf_space}."
    )

    expected_total = num_shelves * sum(bay_widths[:num_bays])
    assert total_usable_shelf_space == expected_total, (
        f"total_usable_shelf_space={total_usable_shelf_space}, but num_shelves * sum(active bay widths)={expected_total}."
    )

    # 8) Optional optimality tag
    sol_opt = "sat"
    if ref_opt_val is not None:
        assert isinstance(ref_opt_val, int), "ref_opt_val must be an int when provided"
        sol_opt = "optimal" if total_usable_shelf_space == ref_opt_val else "sat"

    return "pass", sol_opt
