from cpmpy import *
import json



def build_model(thickness, cut_cost, vertical_gap, lengths, book_groups):
    """
    Bookshelf Design Problem - CR1

    CR1: Shelf spacing is no longer uniform. Each used shelf compartment may
    have its own vertical clearance, and book-group demand width can be
    allocated across shelf compartments that are tall enough.

    thickness: thickness of planks
    cut_cost: length lost each time a plank is cut
    vertical_gap: minimum baseline vertical clearance for any used shelf
    lengths: list of available plank lengths
    book_groups: list of {"min_clearance": int, "demand_width": int}
    """

    if vertical_gap < 0:
        raise ValueError("vertical_gap must be non-negative")
    if not book_groups:
        raise ValueError("book_groups must be non-empty")

    required_keys = {"min_clearance", "demand_width"}
    for idx, group in enumerate(book_groups):
        if set(group.keys()) != required_keys:
            raise ValueError(
                f"book_groups[{idx}] must contain exactly {sorted(required_keys)}"
            )
        if group["min_clearance"] < 0:
            raise ValueError(f"book_groups[{idx}].min_clearance must be non-negative")
        if group["demand_width"] < 0:
            raise ValueError(f"book_groups[{idx}].demand_width must be non-negative")

    n_planks = len(lengths)
    max_len = max(lengths)

    # Maximum number of pieces based on the smallest possible shelf clearance.
    max_pieces = 2 + (max_len // (thickness + vertical_gap))
    n_levels = max_pieces - 2

    n_groups = len(book_groups)
    min_clearances = [group["min_clearance"] for group in book_groups]
    demand_widths = [group["demand_width"] for group in book_groups]
    max_demand = max(demand_widths)
    total_demand = sum(demand_widths)

    # piece_lengths[i] = length of piece i, 0 means unused
    piece_lengths = intvar(0, max_len, shape=max_pieces, name="piece_lengths")

    # piece_from[i] = plank index that piece i comes from
    piece_from = intvar(0, n_planks - 1, shape=max_pieces, name="piece_from")

    # used[i] = whether piece i is actually used
    used = boolvar(shape=max_pieces, name="used")

    # all shelves have the same width
    shelf_width = intvar(0, max_len, name="shelf_width")

    # uprights have equal height
    unit_height = intvar(0, max_len, name="unit_height")

    # number of shelves
    n_shelves = intvar(1, max_pieces - 2, name="n_shelves")

    # helper variables per plank
    pieces_from_plank = intvar(0, max_pieces, shape=n_planks, name="pieces_from_plank")
    cut_loss = intvar(0, max_pieces - 1, shape=n_planks, name="cut_loss")
    has_piece = boolvar(shape=n_planks, name="has_piece")

    # CR1: shelf-specific clearances and book-group allocation
    shelf_clearance = intvar(0, max_len, shape=n_levels, name="shelf_clearance")
    allocated_width = intvar(0, max_demand, shape=(n_groups, n_levels), name="allocated_width")
    group_on_shelf = boolvar(shape=(n_groups, n_levels), name="group_on_shelf")
    total_accommodated_width = intvar(0, total_demand, name="total_accommodated_width")

    model = Model()

    # ------------------------------------------------
    # 1. Used pieces are packed at the start
    # ------------------------------------------------
    for i in range(max_pieces):
        model += used[i] == (piece_lengths[i] > 0)

    for i in range(max_pieces - 1):
        model += used[i] >= used[i + 1]

    # Need at least two uprights and one shelf
    model += used[0]
    model += used[1]
    model += used[2]

    # ------------------------------------------------
    # 2. Uprights
    # ------------------------------------------------
    model += piece_lengths[0] == piece_lengths[1]
    model += unit_height == piece_lengths[0]

    # ------------------------------------------------
    # 3. Shelves: all used shelf pieces have same width
    # ------------------------------------------------
    model += shelf_width == piece_lengths[2]

    for i in range(2, max_pieces):
        model += used[i].implies(piece_lengths[i] == shelf_width)
        model += (~used[i]).implies(piece_lengths[i] == 0)

    model += n_shelves == sum(used[i] for i in range(2, max_pieces))

    # ------------------------------------------------
    # 4. CR1: shelf clearances can vary by level
    # ------------------------------------------------
    for s in range(n_levels):
        model += (~used[s + 2]).implies(shelf_clearance[s] == 0)
        model += used[s + 2].implies(shelf_clearance[s] >= vertical_gap)

    model += unit_height >= sum(shelf_clearance) + thickness * n_shelves

    # ------------------------------------------------
    # 5. Do not overuse any plank
    # ------------------------------------------------
    for p in range(n_planks):
        model += pieces_from_plank[p] == sum(
            (piece_from[i] == p) & used[i] for i in range(max_pieces)
        )

        model += has_piece[p] == (pieces_from_plank[p] >= 1)

        # if a plank yields k pieces, it incurs k-1 cuts
        model += cut_loss[p] == pieces_from_plank[p] - has_piece[p]

        model += (
            sum(piece_lengths[i] * (piece_from[i] == p) for i in range(max_pieces))
            + cut_cost * cut_loss[p]
            <= lengths[p]
        )

    # ------------------------------------------------
    # 6. CR1: allocate book-group demand across shelves
    # ------------------------------------------------
    for g in range(n_groups):
        for s in range(n_levels):
            model += allocated_width[g, s] <= demand_widths[g] * group_on_shelf[g, s]
            model += group_on_shelf[g, s].implies(allocated_width[g, s] >= 1)
            model += group_on_shelf[g, s] <= used[s + 2]
            model += group_on_shelf[g, s].implies(
                shelf_clearance[s] >= min_clearances[g]
            )

        model += sum(allocated_width[g, s] for s in range(n_levels)) <= demand_widths[g]

    for s in range(n_levels):
        model += sum(allocated_width[g, s] for g in range(n_groups)) <= shelf_width

    model += total_accommodated_width == sum(
        allocated_width[g, s] for g in range(n_groups) for s in range(n_levels)
    )

    # ------------------------------------------------
    # 7. CR1: maximize accommodated book demand
    # ------------------------------------------------
    model.maximize(total_accommodated_width)

    return (
        model,
        piece_lengths,
        piece_from,
        n_shelves,
        shelf_width,
        unit_height,
        shelf_clearance,
        allocated_width,
        total_accommodated_width,
    )


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    (
        model,
        piece_lengths,
        piece_from,
        n_shelves,
        shelf_width,
        unit_height,
        shelf_clearance,
        allocated_width,
        total_accommodated_width,
    ) = build_model(
        data["thickness"],
        data["cut_cost"],
        data["vertical_gap"],
        data["lengths"],
        data["book_groups"],
    )

    if model.solve():
        solution = {
            "piece_lengths": piece_lengths.value().tolist(),
            "piece_from": piece_from.value().tolist(),
            "num_shelves": int(n_shelves.value()),
            "shelf_width": int(shelf_width.value()),
            "unit_height": int(unit_height.value()),
            "shelf_clearances": shelf_clearance.value().tolist(),
            "allocated_widths": allocated_width.value().tolist(),
            "total_accommodated_width": int(total_accommodated_width.value()),
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
