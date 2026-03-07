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
def cr2_verify_func(data_dict, hypothesis_solution):
    """
    Verify Problem 9 CR2 (restricted deck regions):
    - Output format checks
    - In-deck placement
    - Pairwise non-overlap with class-based separation
    - No container overlaps any restricted region
    """
    deck_width = data_dict["deck_width"]
    deck_length = data_dict["deck_length"]
    n_containers = data_dict["n_containers"]
    width = data_dict["width"]
    length = data_dict["length"]
    classes = data_dict["classes"]
    separation = data_dict["separation"]
    restricted_regions = data_dict["restricted_regions"]

    try:
        x = hypothesis_solution["x"]
        y = hypothesis_solution["y"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    # 1) Basic shape checks
    assert len(x) == n_containers, f"Error: x must have length {n_containers}."
    assert len(y) == n_containers, f"Error: y must have length {n_containers}."
    assert len(width) == n_containers, "Error: width length mismatch."
    assert len(length) == n_containers, "Error: length length mismatch."
    assert len(classes) == n_containers, "Error: classes length mismatch."

    n_classes = len(separation)
    for row in separation:
        assert len(row) == n_classes, "Error: separation must be a square matrix."

    # 2) Domain checks + in-deck placement
    for i in range(n_containers):
        assert isinstance(x[i], int), f"Error: x[{i}] must be int."
        assert isinstance(y[i], int), f"Error: y[{i}] must be int."
        assert 0 <= x[i] <= deck_width, f"Error: x[{i}] out of deck range."
        assert 0 <= y[i] <= deck_length, f"Error: y[{i}] out of deck range."
        assert x[i] + width[i] <= deck_width, (
            f"Error: container {i} exceeds deck width."
        )
        assert y[i] + length[i] <= deck_length, (
            f"Error: container {i} exceeds deck length."
        )

    # 3) Pairwise non-overlap with class-based separation
    for i in range(n_containers):
        c1 = classes[i] - 1
        assert 0 <= c1 < n_classes, f"Error: invalid class for container {i}."
        for j in range(i + 1, n_containers):
            c2 = classes[j] - 1
            assert 0 <= c2 < n_classes, f"Error: invalid class for container {j}."
            sep = separation[c1][c2]
            assert isinstance(sep, int) and sep >= 0, (
                "Error: separation values must be non-negative integers."
            )

            disjoint = (
                (x[i] + width[i] + sep <= x[j]) or
                (x[j] + width[j] + sep <= x[i]) or
                (y[i] + length[i] + sep <= y[j]) or
                (y[j] + length[j] + sep <= y[i])
            )
            assert disjoint, (
                f"Error: containers {i} and {j} overlap or violate separation requirement."
            )

    # 4) CR2: container rectangles must not overlap restricted regions
    for ridx, reg in enumerate(restricted_regions):
        assert isinstance(reg, list) and len(reg) == 4, (
            f"Error: restricted_regions[{ridx}] must be [rx, ry, rw, rl]."
        )
        rx, ry, rw, rl = reg
        assert all(isinstance(v, int) for v in [rx, ry, rw, rl]), (
            f"Error: restricted_regions[{ridx}] entries must be integers."
        )
        assert rw > 0 and rl > 0, f"Error: restricted region {ridx} must have positive size."
        assert 0 <= rx and 0 <= ry and rx + rw <= deck_width and ry + rl <= deck_length, (
            f"Error: restricted region {ridx} must lie fully inside the deck."
        )

        for i in range(n_containers):
            outside = (
                (x[i] + width[i] <= rx) or
                (rx + rw <= x[i]) or
                (y[i] + length[i] <= ry) or
                (ry + rl <= y[i])
            )
            assert outside, (
                f"Error: container {i} overlaps restricted region {ridx}."
            )

    return "pass"
