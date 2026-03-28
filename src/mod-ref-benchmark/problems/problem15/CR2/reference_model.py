from cpmpy import *
import json


def build_model(n_items, bid_values, bid_items, bid_variants):
    """
    Winner Determination Problem for a Combinatorial Auction - CR2.

    Each bid may be satisfied by one of several alternative bundle variants.
    If a bid is accepted, exactly one of its admissible variants must be chosen.
    """

    n_bids = len(bid_values)

    if len(bid_items) != n_bids:
        raise ValueError("bid_values and bid_items must have the same length")
    if len(bid_variants) != n_bids:
        raise ValueError("bid_values and bid_variants must have the same length")

    max_variant_count = 0
    for b in range(n_bids):
        if not bid_variants[b]:
            raise ValueError(f"bid_variants[{b}] must be non-empty")
        if bid_items[b] != bid_variants[b][0]:
            raise ValueError(
                f"bid_items[{b}] must match the first listed variant in bid_variants[{b}]"
            )
        max_variant_count = max(max_variant_count, len(bid_variants[b]))
        for v, bundle in enumerate(bid_variants[b]):
            if len(set(bundle)) != len(bundle):
                raise ValueError(f"bid_variants[{b}][{v}] may not contain duplicate items")
            for item in bundle:
                if not isinstance(item, int) or not (1 <= item <= n_items):
                    raise ValueError(
                        f"bid_variants[{b}][{v}] contains invalid item {item}"
                    )

    # x[b] = 1 iff bid b is accepted
    x = boolvar(shape=n_bids, name="x")

    # y[b,v] = 1 iff bid b is accepted using variant v
    y = boolvar(shape=(n_bids, max_variant_count), name="y")

    revenue = intvar(0, sum(bid_values), name="revenue")

    model = Model()

    # CR2: exactly one admissible variant is chosen iff the bid is accepted.
    for b in range(n_bids):
        for v in range(len(bid_variants[b]), max_variant_count):
            model += y[b, v] == 0
        model += sum(y[b, v] for v in range(len(bid_variants[b]))) == x[b]

    # For each item, at most one chosen bid variant can contain it.
    for item in range(1, n_items + 1):
        containing_variants = []
        for b in range(n_bids):
            for v, bundle in enumerate(bid_variants[b]):
                if item in bundle:
                    containing_variants.append(y[b, v])
        if containing_variants:
            model += sum(containing_variants) <= 1

    # Total revenue
    model += revenue == sum(bid_values[b] * x[b] for b in range(n_bids))

    # Maximize total accepted bid value
    model.maximize(revenue)

    return model, x, y, revenue


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, x, y, revenue = build_model(
        data["n_items"],
        data["bid_values"],
        data["bid_items"],
        data["bid_variants"],
    )

    if model.solve():
        selected_bids = [i for i in range(len(data["bid_values"])) if x[i].value() == 1]
        chosen_variants = []
        for b in range(len(data["bid_values"])):
            chosen_variant = -1
            for v in range(len(data["bid_variants"][b])):
                if y[b, v].value() == 1:
                    chosen_variant = v
                    break
            chosen_variants.append(chosen_variant)

        solution = {
            "selected_bids": selected_bids,
            "chosen_variants": chosen_variants,
            "revenue": int(revenue.value()),
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
