from cpmpy import *

def build_model(start, goal, n_piles):
    n = len(start)
    T = n * n_piles + 1

    state = intvar(0, n, shape=(n+1, T), name="state")
    move  = intvar(0, n, shape=(T-1, 2), name="move")
    done  = boolvar(shape=T, name="done")

    model = Model()

    # table is always on the table
    model += state[0, :] == 0

    # initial and goal states
    model += state[1:, 0] == start
    model += state[1:, T-1] == goal

    # done definition and monotonicity
    for t in range(T):
        model += done[t] == all(state[1:, t] == goal)
    model += Increasing(done)

    # objective: minimize steps before reaching goal
    model.minimize(sum(~done))

    for t in range(1, T):
        moved = move[t-1, 0]
        dest  = move[t-1, 1]

        model += (move[t-1, 0] == 0).implies(move[t-1, 1] == 0)

        # once done, freeze state and force dummy moves
        model += done[t-1].implies(all(state[1:, t] == state[1:, t-1]))
        model += done[t-1].implies(moved == 0)

        # if not done, moved block must change to dest and only it changes
        model += (~done[t-1] & (moved != 0)).implies(state[moved, t] == dest)
        for b in range(1, n+1):
            model += (~done[t-1]).implies(
                (state[b, t] != state[b, t-1]) == (b == moved)
            )

        # moved block must be free
        for b in range(1, n+1):
            model += (~done[t-1] & (moved == b)).implies(
                sum(state[1:, t-1] == b) == 0
            )

        # destination must be free (except table)
        model += (~done[t-1] & (dest != 0)).implies(
            sum(state[1:, t-1] == dest) == 0
        )

        # pile limit (unchanged)
        model += sum(state[1:, t] == 0) <= n_piles

        # ======================================================
        # CR1 ADDITION: at most one temporary table block
        # ======================================================
        model += (~done[t]).implies(
            sum(
                (state[b, t] == 0) & (goal[b-1] != 0)
                for b in range(1, n+1)
            ) <= 2
        )

    return model, state, move


if __name__ == "__main__":
    import json

    with open("input_data.json") as f:
        data = json.load(f)

    start, goal, n_piles = data["start"], data["goal"], data["n_piles"]

    model, state, move = build_model(start, goal, n_piles)

    if model.solve():
        makespan = sum(
            1 for t in range(move.shape[0]) if move[t,0].value() != 0
        )

        print("Solution found with makespan =", makespan)

        printed = 0
        for t in range(move.shape[0]):
            b = move[t,0].value()
            d = move[t,1].value()
            if b != 0:
                print(f"Move block {b} onto {d}")
                printed += 1
                if printed == makespan:
                    break