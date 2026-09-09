import numpy as np


def create_test_depth(rows=50, cols=50):
    """
    Temporary fake depth map.

    This simulates the H x W NumPy array
    that Depth Anything V2 will eventually provide.
    """

    depth = np.zeros((rows, cols), dtype=np.float32)

    center_row = rows / 2
    center_col = cols / 2

    for row in range(rows):
        for col in range(cols):

            distance = (
                (row - center_row) ** 2
                + (col - center_col) ** 2
            ) ** 0.5

            height = 10 - (distance / 5)

            depth[row, col] = max(0, height)

    return depth