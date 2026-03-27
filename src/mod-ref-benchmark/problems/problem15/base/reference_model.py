from cpmpy import *
import json


def build_model(bid_values, bid_items, n_items=None):
    """
    Winner Determination Problem for a Combinatorial Auction.

    bid_values: list[int], scaled integer value of each bid
    bid_items: list[list[int]], items requested by each bid
    n_items: optional total number of items; if omitted, inferred from bid_items
    """

    n_bids = len(bid_values)

    if len(bid_items) != n_bids:
        raise ValueError("bid_values and bid_items must have the same length")

    if n_items is None:
        n_items = max(item for items in bid_items for item in items)

    # x[b] = 1 iff bid b is accepted
    x = boolvar(shape=n_bids, name="x")

    # explicit objective variable for reporting
    revenue = intvar(0, sum(bid_values), name="revenue")

    model = Model()

    # For each item, at most one accepted bid can contain it
    for item in range(1, n_items + 1):
        containing_bids = [b for b in range(n_bids) if item in bid_items[b]]
        if containing_bids:
            model += sum(x[b] for b in containing_bids) <= 1

    # Total revenue
    model += revenue == sum(bid_values[b] * x[b] for b in range(n_bids))

    # Maximize total accepted bid value
    model.maximize(revenue)

    return model, x, revenue

