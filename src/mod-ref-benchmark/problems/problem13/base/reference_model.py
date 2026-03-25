from cpmpy import *
import json


def build_model(thickness, cut_cost, vertical_gap, lengths):
    """
    Bookshelves optimization model.

    thickness: thickness of planks
    cut_cost: length lost each time a plank is cut
    vertical_gap: vertical clearance needed per shelf
    lengths: list of available plank lengths
    """

    n_planks = len(lengths)
    max_len = max(lengths)

    # Maximum number of pieces:
    # 2 uprights + at most max_len // (thickness + vertical_gap) shelves
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
    # 4. Uprights must be tall enough for shelves
    # ------------------------------------------------
    model += unit_height >= n_shelves * (thickness + vertical_gap)

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
    # 6. Objective: maximize total shelf width
    # ------------------------------------------------
    model.maximize(sum(piece_lengths[i] for i in range(2, max_pieces)))

    return model, piece_lengths, piece_from, n_shelves, shelf_width, unit_height


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, piece_lengths, piece_from, n_shelves, shelf_width, unit_height = build_model(
        data["thickness"],
        data["cut_cost"],
        data["vertical_gap"],
        data["lengths"]
    )

    solution = {}

    if model.solve():
        solution["piece_lengths"] = piece_lengths.value().tolist()
        solution["piece_from"] = piece_from.value().tolist()
        solution["num_shelves"] = int(n_shelves.value())
        solution["shelf_width"] = int(shelf_width.value())
        solution["unit_height"] = int(unit_height.value())

    print(json.dumps(solution))