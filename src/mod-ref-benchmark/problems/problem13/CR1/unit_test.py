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
def cr1_verify_func(data_dict, hypothesis_solution):
    """
    Verify Bookshelf Design CR1:
    - Base constraints: packed used pieces, equal uprights, common shelf width,
      plank cutting feasibility
    - CR1 constraints: shelf-specific clearances and book-group width allocation
    - Objective: maximize total accommodated demand width
    """
    thickness = data_dict["thickness"]
    cut_cost = data_dict["cut_cost"]
    vertical_gap = data_dict["vertical_gap"]
    lengths = data_dict["lengths"]
    book_groups = data_dict["book_groups"]
    ref_opt_val = data_dict.get("ref_opt_val", None)

    n_planks = len(lengths)
    max_len = max(lengths)
    max_pieces = 2 + (max_len // (thickness + vertical_gap))
    n_levels = max_pieces - 2
    n_groups = len(book_groups)
    min_clearances = [group["min_clearance"] for group in book_groups]
    demand_widths = [group["demand_width"] for group in book_groups]
    total_demand = sum(demand_widths)

    try:
        piece_lengths = hypothesis_solution["piece_lengths"]
        piece_from = hypothesis_solution["piece_from"]
        num_shelves = hypothesis_solution["num_shelves"]
        shelf_width = hypothesis_solution["shelf_width"]
        unit_height = hypothesis_solution["unit_height"]
        shelf_clearances = hypothesis_solution["shelf_clearances"]
        allocated_widths = hypothesis_solution["allocated_widths"]
        total_accommodated_width = hypothesis_solution["total_accommodated_width"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    # 1) Basic shape and type checks
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

    assert isinstance(num_shelves, int), "num_shelves must be an int"
    assert 1 <= num_shelves <= n_levels, (
        f"num_shelves={num_shelves} out of range [1, {n_levels}]"
    )

    assert isinstance(shelf_width, int), "shelf_width must be an int"
    assert 0 <= shelf_width <= max_len, (
        f"shelf_width={shelf_width} out of range [0, {max_len}]"
    )

    assert isinstance(unit_height, int), "unit_height must be an int"
    assert 0 <= unit_height <= max_len, (
        f"unit_height={unit_height} out of range [0, {max_len}]"
    )

    assert isinstance(shelf_clearances, list), "shelf_clearances must be a list"
    assert len(shelf_clearances) == n_levels, (
        f"shelf_clearances must have length {n_levels}, got {len(shelf_clearances)}"
    )
    for s, val in enumerate(shelf_clearances):
        assert isinstance(val, int), f"shelf_clearances[{s}] must be an int"
        assert 0 <= val <= max_len, (
            f"shelf_clearances[{s}]={val} out of range [0, {max_len}]"
        )

    assert isinstance(allocated_widths, list), "allocated_widths must be a list"
    assert len(allocated_widths) == n_groups, (
        f"allocated_widths must have {n_groups} rows, got {len(allocated_widths)}"
    )
    for g in range(n_groups):
        row = allocated_widths[g]
        assert isinstance(row, list), f"allocated_widths[{g}] must be a list"
        assert len(row) == n_levels, (
            f"allocated_widths[{g}] must have length {n_levels}, got {len(row)}"
        )
        for s, val in enumerate(row):
            assert isinstance(val, int), f"allocated_widths[{g}][{s}] must be an int"
            assert 0 <= val <= demand_widths[g], (
                f"allocated_widths[{g}][{s}]={val} out of range [0, {demand_widths[g]}]"
            )

    assert isinstance(total_accommodated_width, int), (
        "total_accommodated_width must be an int"
    )
    assert 0 <= total_accommodated_width <= total_demand, (
        f"total_accommodated_width={total_accommodated_width} out of range [0, {total_demand}]"
    )

    # 2) Base constraints: packed used pieces and shelf structure
    used = [1 if val > 0 else 0 for val in piece_lengths]
    for i in range(max_pieces - 1):
        assert used[i] >= used[i + 1], (
            f"Used pieces are not packed at the start at indices {i} and {i + 1}."
        )

    assert used[0] == 1, "The first upright must be used."
    assert used[1] == 1, "The second upright must be used."
    assert used[2] == 1, "At least one shelf must be used."

    assert piece_lengths[0] == piece_lengths[1], (
        f"Uprights must have equal height, got {piece_lengths[0]} and {piece_lengths[1]}."
    )
    assert unit_height == piece_lengths[0], (
        f"unit_height={unit_height} must equal the upright height {piece_lengths[0]}."
    )

    assert shelf_width == piece_lengths[2], (
        f"shelf_width={shelf_width} must equal piece_lengths[2]={piece_lengths[2]}."
    )

    recomputed_n_shelves = sum(used[i] for i in range(2, max_pieces))
    assert num_shelves == recomputed_n_shelves, (
        f"num_shelves={num_shelves}, recomputed={recomputed_n_shelves}."
    )

    for i in range(2, max_pieces):
        if used[i]:
            assert piece_lengths[i] == shelf_width, (
                f"Used shelf piece {i} has length {piece_lengths[i]}, expected {shelf_width}."
            )
        else:
            assert piece_lengths[i] == 0, (
                f"Unused shelf slot {i} must have piece length 0, got {piece_lengths[i]}."
            )

    # 3) CR1 shelf-clearance constraints
    for s in range(n_levels):
        shelf_used = used[s + 2]
        if shelf_used:
            assert shelf_clearances[s] >= vertical_gap, (
                f"Used shelf level {s} has clearance {shelf_clearances[s]}, below vertical_gap={vertical_gap}."
            )
        else:
            assert shelf_clearances[s] == 0, (
                f"Unused shelf level {s} must have clearance 0, got {shelf_clearances[s]}."
            )

    assert unit_height >= sum(shelf_clearances) + thickness * num_shelves, (
        f"unit_height={unit_height} is too small for the shelf layout: need at least "
        f"{sum(shelf_clearances) + thickness * num_shelves}."
    )

    # 4) Base cutting feasibility per plank
    for p in range(n_planks):
        pieces_on_plank = [
            i for i in range(max_pieces) if used[i] and piece_from[i] == p
        ]
        total_piece_length = sum(piece_lengths[i] for i in pieces_on_plank)
        cuts = max(0, len(pieces_on_plank) - 1)
        consumed_length = total_piece_length + cut_cost * cuts
        assert consumed_length <= lengths[p], (
            f"Plank {p} is overused: consumed {consumed_length}, available {lengths[p]}."
        )

    # 5) CR1 allocation feasibility
    for g in range(n_groups):
        allocated_for_group = sum(allocated_widths[g][s] for s in range(n_levels))
        assert allocated_for_group <= demand_widths[g], (
            f"Book group {g} exceeds demand: allocated {allocated_for_group}, demand {demand_widths[g]}."
        )
        for s in range(n_levels):
            width = allocated_widths[g][s]
            if width > 0:
                assert used[s + 2] == 1, (
                    f"Book group {g} allocates width to unused shelf level {s}."
                )
                assert shelf_clearances[s] >= min_clearances[g], (
                    f"Book group {g} requires clearance {min_clearances[g]} but shelf level {s} has {shelf_clearances[s]}."
                )

    for s in range(n_levels):
        total_width_on_shelf = sum(allocated_widths[g][s] for g in range(n_groups))
        assert total_width_on_shelf <= shelf_width, (
            f"Shelf level {s} exceeds width capacity: {total_width_on_shelf} > {shelf_width}."
        )
        if used[s + 2] == 0:
            assert total_width_on_shelf == 0, (
                f"Unused shelf level {s} must have zero allocated width, got {total_width_on_shelf}."
            )

    # 6) Objective consistency
    recomputed_total_accommodated_width = sum(
        allocated_widths[g][s] for g in range(n_groups) for s in range(n_levels)
    )
    assert total_accommodated_width == recomputed_total_accommodated_width, (
        f"total_accommodated_width={total_accommodated_width}, "
        f"recomputed={recomputed_total_accommodated_width}."
    )

    # 7) Optional optimality tag
    sol_opt = "sat"
    if ref_opt_val is not None:
        assert isinstance(ref_opt_val, int), "ref_opt_val must be an int when provided"
        sol_opt = "optimal" if total_accommodated_width == ref_opt_val else "sat"

    return "pass", sol_opt
