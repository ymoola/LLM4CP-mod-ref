from cpmpy import *
import json


def build_model(n_items, bid_values, bid_items, bid_quantities, item_capacities):
    """
    Winner Determination Problem for a Combinatorial Auction - CR1.

    Items are item types with available quantities.
    Bid b requests quantities `bid_quantities[b]` for the corresponding
    item types listed in `bid_items[b]`.
    """

    n_bids = len(bid_values)

    if len(bid_items) != n_bids:
        raise ValueError("bid_values and bid_items must have the same length")
    if len(bid_quantities) != n_bids:
        raise ValueError("bid_values and bid_quantities must have the same length")
    if len(item_capacities) != n_items:
        raise ValueError("item_capacities must have length n_items")

    for i, cap in enumerate(item_capacities):
        if not isinstance(cap, int) or cap < 0:
            raise ValueError(f"item_capacities[{i}] must be a non-negative integer")

    for b in range(n_bids):
        if len(bid_items[b]) != len(bid_quantities[b]):
            raise ValueError(
                f"bid_items[{b}] and bid_quantities[{b}] must have the same length"
            )
        if len(set(bid_items[b])) != len(bid_items[b]):
            raise ValueError(f"bid_items[{b}] may not contain duplicate item types")
        for item in bid_items[b]:
            if not isinstance(item, int) or not (1 <= item <= n_items):
                raise ValueError(f"bid_items[{b}] contains invalid item type {item}")
        for q in bid_quantities[b]:
            if not isinstance(q, int) or q <= 0:
                raise ValueError(f"bid_quantities[{b}] must contain positive integers")

    # x[b] = 1 iff bid b is accepted
    x = boolvar(shape=n_bids, name="x")

    # explicit objective variable for reporting
    revenue = intvar(0, sum(bid_values), name="revenue")

    model = Model()

    # CR1: For each item type, accepted bids cannot exceed available quantity.
    for item in range(1, n_items + 1):
        terms = []
        for b in range(n_bids):
            qty = 0
            for bid_item, q in zip(bid_items[b], bid_quantities[b]):
                if bid_item == item:
                    qty = q
                    break
            if qty > 0:
                terms.append(qty * x[b])
        model += sum(terms) <= item_capacities[item - 1]

    # Total revenue
    model += revenue == sum(bid_values[b] * x[b] for b in range(n_bids))

    # Maximize total accepted bid value
    model.maximize(revenue)

    return model, x, revenue


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, x, revenue = build_model(
        data["n_items"],
        data["bid_values"],
        data["bid_items"],
        data["bid_quantities"],
        data["item_capacities"],
    )

    if model.solve():
        solution = {
            "selected_bids": [i for i in range(len(data["bid_values"])) if x[i].value() == 1],
            "revenue": int(revenue.value()),
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
