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
def cr1_verify_func(data_dict, hypothesis_solution):
    """
    Verify Problem 9 CR1 (container rotation):
    - Output format checks
    - Rotation semantics for effective dimensions
    - In-deck placement
    - Pairwise non-overlap with class-based separation
    """
    deck_width = data_dict["deck_width"]
    deck_length = data_dict["deck_length"]
    n_containers = data_dict["n_containers"]
    width = data_dict["width"]
    length = data_dict["length"]
    classes = data_dict["classes"]
    separation = data_dict["separation"]

    try:
        x = hypothesis_solution["x"]
        y = hypothesis_solution["y"]
        rot = hypothesis_solution["rot"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    # 1) Basic shape checks
    assert len(x) == n_containers, f"Error: x must have length {n_containers}."
    assert len(y) == n_containers, f"Error: y must have length {n_containers}."
    assert len(rot) == n_containers, f"Error: rot must have length {n_containers}."
    assert len(width) == n_containers, "Error: width length mismatch."
    assert len(length) == n_containers, "Error: length length mismatch."
    assert len(classes) == n_containers, "Error: classes length mismatch."

    n_classes = len(separation)
    for r in separation:
        assert len(r) == n_classes, "Error: separation must be a square matrix."

    # 2) Domain checks and effective dimensions under rotation
    eff_w = [0] * n_containers
    eff_l = [0] * n_containers

    for i in range(n_containers):
        assert isinstance(x[i], int), f"Error: x[{i}] must be int."
        assert isinstance(y[i], int), f"Error: y[{i}] must be int."
        assert 0 <= x[i] <= deck_width, f"Error: x[{i}] out of deck range."
        assert 0 <= y[i] <= deck_length, f"Error: y[{i}] out of deck range."

        # Accept bool or 0/1 for rotation
        r_i = rot[i]
        if isinstance(r_i, bool):
            r_i = int(r_i)
        assert isinstance(r_i, int) and r_i in [0, 1], f"Error: rot[{i}] must be 0/1."

        # CR1 rotation semantics
        if r_i == 0:
            eff_w[i] = width[i]
            eff_l[i] = length[i]
        else:
            eff_w[i] = length[i]
            eff_l[i] = width[i]

        # In-deck bounds using effective dimensions
        assert x[i] + eff_w[i] <= deck_width, (
            f"Error: container {i} exceeds deck width after rotation handling."
        )
        assert y[i] + eff_l[i] <= deck_length, (
            f"Error: container {i} exceeds deck length after rotation handling."
        )

    # 3) Non-overlap with required class separation
    for i in range(n_containers):
        c1 = classes[i] - 1
        assert 0 <= c1 < n_classes, f"Error: invalid class for container {i}."
        for j in range(i + 1, n_containers):
            c2 = classes[j] - 1
            assert 0 <= c2 < n_classes, f"Error: invalid class for container {j}."
            sep = separation[c1][c2]
            assert isinstance(sep, int) and sep >= 0, "Error: separation values must be non-negative integers."

            disjoint = (
                (x[i] + eff_w[i] + sep <= x[j]) or
                (x[j] + eff_w[j] + sep <= x[i]) or
                (y[i] + eff_l[i] + sep <= y[j]) or
                (y[j] + eff_l[j] + sep <= y[i])
            )
            assert disjoint, (
                f"Error: containers {i} and {j} overlap or violate separation requirement."
            )

    return "pass"
