from cpmpy import *
import json



def build_model(thickness, cut_cost, vertical_gap, lengths, max_bays):
    """
    Bookshelf Design Problem - CR2

    CR2: The bookshelf may include optional full-height internal dividers,
    creating between 1 and max_bays side-by-side bays. Each used shelf level
    contains one shelf piece in every used bay.

    thickness: thickness of planks
    cut_cost: length lost each time a plank is cut
    vertical_gap: vertical clearance needed per shelf level
    lengths: list of available plank lengths
    max_bays: maximum number of bays allowed in the design
    """

    if max_bays < 1 or max_bays > 3:
        raise ValueError("max_bays must be between 1 and 3")
    if vertical_gap < 0:
        raise ValueError("vertical_gap must be non-negative")
    if not lengths:
        raise ValueError("lengths must be non-empty")

    n_planks = len(lengths)
    max_len = max(lengths)
    max_shelves = max_len // (thickness + vertical_gap)
    if max_shelves < 1:
        raise ValueError("No shelf level fits under the given thickness and vertical_gap")

    max_verticals = max_bays + 1
    max_pieces = max_verticals + max_shelves * max_bays

    # piece_lengths[i] = length of piece i, 0 means unused
    piece_lengths = intvar(0, max_len, shape=max_pieces, name="piece_lengths")

    # piece_from[i] = plank index that piece i comes from
    piece_from = intvar(0, n_planks - 1, shape=max_pieces, name="piece_from")

    # used[i] = whether piece i is actually used
    used = boolvar(shape=max_pieces, name="used")

    # common height of outer panels and dividers
    unit_height = intvar(0, max_len, name="unit_height")

    # number of shelf levels repeated across every used bay
    n_shelves = intvar(1, max_shelves, name="n_shelves")

    # CR2: number of bays and bay widths
    n_bays = intvar(1, max_bays, name="n_bays")
    bay_widths = intvar(0, max_len, shape=max_bays, name="bay_widths")
    bay_used = boolvar(shape=max_bays, name="bay_used")
    level_used = boolvar(shape=max_shelves, name="level_used")

    # helper variables per plank
    pieces_from_plank = intvar(0, max_pieces, shape=n_planks, name="pieces_from_plank")
    cut_loss = intvar(0, max_pieces - 1, shape=n_planks, name="cut_loss")
    has_piece = boolvar(shape=n_planks, name="has_piece")

    total_usable_shelf_space = intvar(
        0, max_bays * max_shelves * max_len, name="total_usable_shelf_space"
    )

    model = Model()

    # ------------------------------------------------
    # 1. CR2: vertical panels are packed in the first slots
    # ------------------------------------------------
    for v in range(max_verticals - 1):
        model += used[v] >= used[v + 1]

    # Need at least the two outer side panels
    model += used[0]
    model += used[1]

    # Number of vertical panels = outer sides + internal dividers = n_bays + 1
    model += sum(used[v] for v in range(max_verticals)) == n_bays + 1

    for v in range(max_verticals):
        model += used[v].implies(piece_lengths[v] == unit_height)
        model += (~used[v]).implies(piece_lengths[v] == 0)

    # ------------------------------------------------
    # 2. CR2: active bays are packed and have widths
    # ------------------------------------------------
    model += bay_used[0]
    for b in range(max_bays - 1):
        model += bay_used[b] >= bay_used[b + 1]
        model += bay_widths[b] >= bay_widths[b + 1]

    model += n_bays == sum(bay_used)

    for b in range(max_bays):
        model += bay_used[b].implies(bay_widths[b] >= 1)
        model += (~bay_used[b]).implies(bay_widths[b] == 0)

    # ------------------------------------------------
    # 3. CR2: shelf levels are packed
    # ------------------------------------------------
    model += level_used[0]
    for s in range(max_shelves - 1):
        model += level_used[s] >= level_used[s + 1]

    model += n_shelves == sum(level_used)

    # ------------------------------------------------
    # 4. CR2: each used shelf level contains one shelf
    # piece in every used bay
    # ------------------------------------------------
    for s in range(max_shelves):
        for b in range(max_bays):
            idx = max_verticals + s * max_bays + b
            model += used[idx] == (level_used[s] & bay_used[b])
            model += used[idx].implies(piece_lengths[idx] == bay_widths[b])
            model += (~used[idx]).implies(piece_lengths[idx] == 0)

    # ------------------------------------------------
    # 5. Uprights/dividers must be tall enough for shelves
    # ------------------------------------------------
    model += unit_height >= n_shelves * (thickness + vertical_gap)

    # ------------------------------------------------
    # 6. Do not overuse any plank
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
    # 7. Objective: maximize total usable shelf space
    # ------------------------------------------------
    shelf_start = max_verticals
    model += total_usable_shelf_space == sum(
        piece_lengths[i] for i in range(shelf_start, max_pieces)
    )
    model.maximize(total_usable_shelf_space)

    return (
        model,
        piece_lengths,
        piece_from,
        n_bays,
        n_shelves,
        bay_widths,
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
        n_bays,
        n_shelves,
        bay_widths,
        unit_height,
        total_usable_shelf_space,
    ) = build_model(
        data["thickness"],
        data["cut_cost"],
        data["vertical_gap"],
        data["lengths"],
        data["max_bays"],
    )

    if model.solve():
        solution = {
            "piece_lengths": piece_lengths.value().tolist(),
            "piece_from": piece_from.value().tolist(),
            "num_bays": int(n_bays.value()),
            "num_shelves": int(n_shelves.value()),
            "bay_widths": bay_widths.value().tolist(),
            "unit_height": int(unit_height.value()),
            "total_usable_shelf_space": int(total_usable_shelf_space.value()),
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
