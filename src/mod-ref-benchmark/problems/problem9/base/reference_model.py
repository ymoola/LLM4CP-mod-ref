from cpmpy import *

def build_model(deck_width, deck_length, n_containers, width, length, classes, separation):

    n = n_containers

    # bottom-left coordinates of containers
    x = intvar(0, deck_width, shape=n, name="x")
    y = intvar(0, deck_length, shape=n, name="y")

    model = Model()


    # Containers must stay inside deck
    for i in range(n):
        model += x[i] + width[i] <= deck_width
        model += y[i] + length[i] <= deck_length

    # Non-overlapping containers
    for i in range(n):
        for j in range(i+1, n):

            c1 = classes[i] - 1
            c2 = classes[j] - 1
            sep = separation[c1][c2]

            model += (
                (x[i] + width[i] + sep <= x[j]) |
                (x[j] + width[j] + sep <= x[i]) |
                (y[i] + length[i] + sep <= y[j]) |
                (y[j] + length[j] + sep <= y[i])
            )

    return model, x, y


