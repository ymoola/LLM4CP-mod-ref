from cpmpy import *


def build_model(start, goal, n_piles):
    n = len(start)
    # Fixed upper bound on makespan: each block can only be moved at most n times
    T = n * n_piles + 1

    # What block is b resting on at time t? 0 means on the table
    state = intvar(0, n, shape=(n+1, T), name="state")
    # Which block is moved at time t and where is it moved to? 0 means no move
    move  = intvar(0, n, shape=(T-1, 2), name="move")
    # True if goal is satisfied at time t 
    done  = boolvar(shape=T, name="done")

    model = Model()

    # table is always on the table
    model += state[0, :] == 0
    # initial and goal states
    model += state[1:, 0] == start
    model += state[1:, T-1] == goal

    # done definition and monotonicity
    for t in range(T):
        # done[t] = True iff every block is in its goal position at time t
        model += done[t] == all(state[1:, t] == goal)
    # Forces done to be monotonic: Once the goal is reached, it stays reached forever
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
            model += (~done[t-1]).implies((state[b, t] != state[b, t-1]) == (b == moved))

        # moved block must be free (no child)
        for b in range(1, n+1):
            model += (~done[t-1] & (moved == b)).implies(sum(state[1:, t-1] == b) == 0)

        # destination must be free
        model += (~done[t-1] & (dest != 0)).implies(
            sum(state[1:, t-1] == dest) == 0
        )

        # pile limit
        model += sum(state[1:, t] == 0) <= n_piles

    return model, move









