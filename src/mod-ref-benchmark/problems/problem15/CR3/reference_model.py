from cpmpy import *
import json


def build_model(n_items, bid_values, bid_items, reserve_values):
    """
    Winner Determination Problem for a Combinatorial Auction - CR3.

    Each item may either be sold through at most one accepted bid or
    reserved for internal use at its reserve value.
    """

    n_bids = len(bid_values)

    if len(bid_items) != n_bids:
        raise ValueError("bid_values and bid_items must have the same length")
    if len(reserve_values) != n_items:
        raise ValueError("reserve_values must have length n_items")

    for i, val in enumerate(reserve_values):
        if not isinstance(val, int) or val < 0:
            raise ValueError(f"reserve_values[{i}] must be a non-negative integer")

    for b in range(n_bids):
        if len(set(bid_items[b])) != len(bid_items[b]):
            raise ValueError(f"bid_items[{b}] may not contain duplicate items")
        for item in bid_items[b]:
            if not isinstance(item, int) or not (1 <= item <= n_items):
                raise ValueError(f"bid_items[{b}] contains invalid item {item}")

    # x[b] = 1 iff bid b is accepted
    x = boolvar(shape=n_bids, name="x")

    # r[i] = 1 iff item i+1 is reserved for internal use
    r = boolvar(shape=n_items, name="r")

    revenue = intvar(0, sum(bid_values), name="revenue")
    reserved_value = intvar(0, sum(reserve_values), name="reserved_value")
    total_value = intvar(0, sum(bid_values) + sum(reserve_values), name="total_value")

    model = Model()

    # CR3: an item can be sold through at most one accepted bid or reserved, but not both.
    for item in range(1, n_items + 1):
        containing_bids = [b for b in range(n_bids) if item in bid_items[b]]
        model += sum(x[b] for b in containing_bids) + r[item - 1] <= 1

    # Total bid revenue
    model += revenue == sum(bid_values[b] * x[b] for b in range(n_bids))

    # Total reserve value from kept items
    model += reserved_value == sum(reserve_values[i] * r[i] for i in range(n_items))

    # Combined objective value
    model += total_value == revenue + reserved_value

    model.maximize(total_value)

    return model, x, r, revenue, reserved_value, total_value


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, x, r, revenue, reserved_value, total_value = build_model(
        data["n_items"],
        data["bid_values"],
        data["bid_items"],
        data["reserve_values"],
    )

    if model.solve():
        solution = {
            "selected_bids": [i for i in range(len(data["bid_values"])) if x[i].value() == 1],
            "reserved_items": [i + 1 for i in range(data["n_items"]) if r[i].value() == 1],
            "revenue": int(revenue.value()),
            "reserved_value": int(reserved_value.value()),
            "total_value": int(total_value.value()),
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
