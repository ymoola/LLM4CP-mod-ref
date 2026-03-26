from cpmpy import *
import json



def build_model(thickness, cut_cost, vertical_gap, lengths, min_bottom_open_height):
    """
    Bookshelf Design Problem - CR3

    CR3: The bookshelf must leave an open bottom zone below the first shelf.

    thickness: thickness of planks
    cut_cost: length lost each time a plank is cut
    vertical_gap: vertical clearance needed per shelf
    lengths: list of available plank lengths
    min_bottom_open_height: minimum open height below the first shelf
    """

    if min_bottom_open_height < 0:
        raise ValueError("min_bottom_open_height must be non-negative")
    if not lengths:
        raise ValueError("lengths must be non-empty")

    n_planks = len(lengths)
    max_len = max(lengths)

    # Maximum number of pieces from the base bound.
    max_pieces = 2 + (max_len // (thickness + vertical_gap))

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

    total_usable_shelf_space = intvar(
        0, (max_pieces - 2) * max_len, name="total_usable_shelf_space"
    )

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
    # 4. CR3: reserve an open bottom zone below the
    # first shelf
    # ------------------------------------------------
    model += (
        unit_height
        >= min_bottom_open_height + n_shelves * (thickness + vertical_gap)
    )

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
    # 6. Objective: maximize total usable shelf space
    # ------------------------------------------------
    model += total_usable_shelf_space == sum(
        piece_lengths[i] for i in range(2, max_pieces)
    )
    model.maximize(total_usable_shelf_space)

    return (
        model,
        piece_lengths,
        piece_from,
        n_shelves,
        shelf_width,
        unit_height,
        total_usable_shelf_space,
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
        total_usable_shelf_space,
    ) = build_model(
        data["thickness"],
        data["cut_cost"],
        data["vertical_gap"],
        data["lengths"],
        data["min_bottom_open_height"],
    )

    if model.solve():
        solution = {
            "piece_lengths": piece_lengths.value().tolist(),
            "piece_from": piece_from.value().tolist(),
            "num_shelves": int(n_shelves.value()),
            "shelf_width": int(shelf_width.value()),
            "unit_height": int(unit_height.value()),
            "total_usable_shelf_space": int(total_usable_shelf_space.value()),
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
