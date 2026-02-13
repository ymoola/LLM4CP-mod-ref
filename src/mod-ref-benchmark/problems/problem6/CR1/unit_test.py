import traceback

def handle_assertions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return {
                "err": repr(str(e)),
                "err_trace": repr(''.join(traceback.format_exception(None, e, e.__traceback__)))
            }
    return wrapper


def _count_children(support):
    """
    support is 1-indexed list-like with support[b] in {0..n}
    Returns child_count[x] = number of blocks directly on x
    """
    n = len(support) - 1
    child_count = [0] * (n + 1)
    for b in range(1, n + 1):
        s = support[b]
        assert 0 <= s <= n, f"Invalid support value support[{b}]={s}"
        child_count[s] += 1
    return child_count


def _assert_acyclic(support):
    """
    Ensures the support pointers form a forest rooted at 0 (table).
    Detects cycles by walking parent pointers from each node.
    """
    n = len(support) - 1
    for b in range(1, n + 1):
        seen = set()
        cur = b
        while cur != 0:
            assert cur not in seen, f"Cycle detected involving block {b}"
            seen.add(cur)
            cur = support[cur]
            assert 0 <= cur <= n, f"Invalid pointer while checking cycles: {cur}"


def _temporary_table_count(support, goal):
    """
    Temporary = on table now (support[b]==0) but goal[b-1] != 0
    """
    n = len(goal)
    temp = 0
    for b in range(1, n + 1):
        if support[b] == 0 and goal[b - 1] != 0:
            temp += 1
    return temp


@handle_assertions
def cr1_verify_func(data_dict, hypothesis_solution):
    """
    Verifies Blocks World constraints + CR: at most temp_limit temporary table blocks at any step.

    Expected in data_dict:
      - start: List[int] length n
      - goal:  List[int] length n
      - n_piles: int
      - (optional) temp_limit: int (defaults to 2)
      - (optional) ref_opt_val: int (for optimality tagging)

    Expected in hypothesis_solution:
      - move: List[List[int]] where each entry [moved, dest]
        moved==0 means no-op; dest can be 0..n (we will require dest==0 when moved==0)
      - (optional) makespan: int (we will recompute and check equality)
    """
    start = data_dict["start"]
    goal = data_dict["goal"]
    n_piles = data_dict["n_piles"]
    temp_limit = data_dict.get("temp_limit", 2)
    ref_opt_val = data_dict.get("ref_opt_val", None)

    try:
        moves = hypothesis_solution["move"]
        reported_makespan = hypothesis_solution.get("makespan", None)
    except Exception as e:
        return f"solFormatError: {e}"

    n = len(start)
    assert len(goal) == n, "start and goal must have same length"
    assert isinstance(n_piles, int) and n_piles >= 1, "n_piles must be an int >= 1"
    assert isinstance(temp_limit, int) and temp_limit >= 0, "temp_limit must be an int >= 0"

    # Support representation: 1-indexed
    support = [0] * (n + 1)
    for b in range(1, n + 1):
        s = start[b - 1]
        assert 0 <= s <= n, f"Invalid start support for block {b}: {s}"
        assert s != b, f"Block {b} cannot rest on itself in start"
        support[b] = s

    # Initial structural checks
    _assert_acyclic(support)
    assert sum(1 for b in range(1, n + 1) if support[b] == 0) <= n_piles, \
        "Start violates n_piles table limit"

    # CR check at initial state
    assert _temporary_table_count(support, goal) <= temp_limit, \
        f"CR violation at t=0: temporary table blocks > {temp_limit}"

    # Simulate moves
    assert isinstance(moves, list), "move must be a list"
    makespan = 0

    for t, mv in enumerate(moves):
        assert isinstance(mv, (list, tuple)) and len(mv) == 2, \
            f"move[{t}] must be [moved, dest]"
        moved, dest = mv
        assert isinstance(moved, int) and isinstance(dest, int), \
            f"move[{t}] entries must be ints"
        assert 0 <= moved <= n, f"move[{t}].moved out of range: {moved}"
        assert 0 <= dest <= n, f"move[{t}].dest out of range: {dest}"

        # If moved == 0, treat as no-op. For cleanliness require dest == 0 as well.
        if moved == 0:
            assert dest == 0, f"move[{t}] is a no-op (moved=0) but dest={dest}, expected dest=0"
            # State unchanged, but still check invariants
            _assert_acyclic(support)
            assert sum(1 for b in range(1, n + 1) if support[b] == 0) <= n_piles, \
                f"n_piles violated at t={t} during no-op"
            assert _temporary_table_count(support, goal) <= temp_limit, \
                f"CR violation at t={t} during no-op"
            continue

        # Real move
        makespan += 1

        # moved cannot be placed on itself
        assert moved != dest, f"move[{t}] invalid: moved block {moved} onto itself"

        # Count children to enforce 'free' conditions
        child_count = _count_children(support)

        # Moved block must be free (no blocks on top)
        assert child_count[moved] == 0, f"move[{t}] invalid: moved block {moved} is not free"

        # Destination must be free if it is a block (table is always allowed)
        if dest != 0:
            assert child_count[dest] == 0, f"move[{t}] invalid: destination block {dest} is not free"

        # Apply move: change support pointer
        support[moved] = dest

        # Structural validity: must remain acyclic
        _assert_acyclic(support)

        # Pile limit after move
        assert sum(1 for b in range(1, n + 1) if support[b] == 0) <= n_piles, \
            f"n_piles violated at t={t} after move"

        # CR constraint after move
        assert _temporary_table_count(support, goal) <= temp_limit, \
            f"CR violation at t={t} after move: temporary table blocks > {temp_limit}"

    # Final state must match goal exactly
    for b in range(1, n + 1):
        assert support[b] == goal[b - 1], \
            f"Final state mismatch for block {b}: got {support[b]}, expected {goal[b-1]}"

    # If a makespan was reported, verify it matches our external computation
    if reported_makespan is not None:
        assert isinstance(reported_makespan, int), "reported makespan must be int"
        assert reported_makespan == makespan, \
            f"Reported makespan={reported_makespan}, recomputed makespan={makespan}"

    # Optional optimality tag
    sol_opt = "sat"
    if ref_opt_val is not None:
        assert isinstance(ref_opt_val, int), "ref_opt_val must be int"
        sol_opt = "optimal" if makespan == ref_opt_val else "sat"

    return "pass", sol_opt
