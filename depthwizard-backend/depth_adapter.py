import numpy as np
from PIL import Image


def prepare_depth(depth):
    """
    Prepare a depth map for DepthWizard.

    Input:
        depth -> H x W NumPy array

    Output:
        processed_depth -> H x W float32 NumPy array
        depth_image -> grayscale PIL image
    """

    # Make sure the input is a NumPy array
    depth = np.asarray(depth, dtype=np.float32)

    # Check dimensions
    if depth.ndim != 2:
        raise ValueError(
            "Depth map must be a 2D H x W array."
        )

    # Remove invalid values
    depth = np.nan_to_num(
        depth,
        nan=0.0,
        posinf=0.0,
        neginf=0.0
    )

    # Find minimum and maximum
    depth_min = float(depth.min())
    depth_max = float(depth.max())

    # Normalize for visualization
    if depth_max > depth_min:

        normalized = (
            (depth - depth_min)
            / (depth_max - depth_min)
            * 255.0
        )

    else:

        normalized = np.zeros_like(
            depth
        )

    # Convert to image
    depth_image = Image.fromarray(
        normalized.astype(np.uint8)
    )

    return depth, depth_image