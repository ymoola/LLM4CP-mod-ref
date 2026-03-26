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
    """
    Verify Bookshelf Design CR3:
    - Base cutting and shelf-width constraints still apply
    - CR3 reserves a minimum open bottom zone below the first shelf
    - Objective remains total usable shelf space
    """
    thickness = data_dict["thickness"]
    cut_cost = data_dict["cut_cost"]
    vertical_gap = data_dict["vertical_gap"]
    lengths = data_dict["lengths"]
    min_bottom_open_height = data_dict["min_bottom_open_height"]
    ref_opt_val = data_dict.get("ref_opt_val", None)

    n_planks = len(lengths)
    max_len = max(lengths)
    max_pieces = 2 + (max_len // (thickness + vertical_gap))

    try:
        piece_lengths = hypothesis_solution["piece_lengths"]
        piece_from = hypothesis_solution["piece_from"]
        num_shelves = hypothesis_solution["num_shelves"]
        shelf_width = hypothesis_solution["shelf_width"]
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

    assert isinstance(num_shelves, int), "num_shelves must be an int"
    assert 1 <= num_shelves <= max_pieces - 2, (
        f"num_shelves={num_shelves} out of range [1, {max_pieces - 2}]"
    )

    assert isinstance(shelf_width, int), "shelf_width must be an int"
    assert 0 <= shelf_width <= max_len, (
        f"shelf_width={shelf_width} out of range [0, {max_len}]"
    )

    assert isinstance(unit_height, int), "unit_height must be an int"
    assert 0 <= unit_height <= max_len, (
        f"unit_height={unit_height} out of range [0, {max_len}]"
    )

    assert isinstance(total_usable_shelf_space, int), (
        "total_usable_shelf_space must be an int"
    )
    assert total_usable_shelf_space >= 0, "total_usable_shelf_space must be non-negative"

    # 2) Base constraints: packed used pieces and common shelf width
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

    recomputed_num_shelves = sum(used[i] for i in range(2, max_pieces))
    assert num_shelves == recomputed_num_shelves, (
        f"num_shelves={num_shelves}, recomputed={recomputed_num_shelves}."
    )

    for i in range(2, max_pieces):
        if used[i]:
            assert piece_lengths[i] == shelf_width, (
                f"Used shelf piece {i} has length {piece_lengths[i]}, expected {shelf_width}."
            )
        else:
            assert piece_lengths[i] == 0, (
                f"Unused shelf slot {i} must have length 0, got {piece_lengths[i]}."
            )

    # 3) CR3 bottom-open-zone constraint
    assert unit_height >= min_bottom_open_height + num_shelves * (thickness + vertical_gap), (
        f"unit_height={unit_height} is too small to leave bottom open height {min_bottom_open_height} "
        f"with {num_shelves} shelves; need at least "
        f"{min_bottom_open_height + num_shelves * (thickness + vertical_gap)}."
    )

    # 4) Base cutting feasibility
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

    # 5) Objective consistency
    recomputed_total_usable_shelf_space = sum(piece_lengths[i] for i in range(2, max_pieces))
    assert total_usable_shelf_space == recomputed_total_usable_shelf_space, (
        f"total_usable_shelf_space={total_usable_shelf_space}, "
        f"recomputed={recomputed_total_usable_shelf_space}."
    )

    # 6) Optional optimality tag
    sol_opt = "sat"
    if ref_opt_val is not None:
        assert isinstance(ref_opt_val, int), "ref_opt_val must be an int when provided"
        sol_opt = "optimal" if total_usable_shelf_space == ref_opt_val else "sat"

    return "pass", sol_opt
