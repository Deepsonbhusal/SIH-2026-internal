from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent

RESULTS_DIR = ROOT / "results" / "mesh"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MESH_SIZE = 256

X_SPACING = 1.0
Y_SPACING = 1.0

VERTICAL_EXAGGERATION = 1.0

BORDER_FRACTION = 0.04

STABILIZE_BOUNDARY = True


def calculate_crop_bounds(
    height: int,
    width: int,
    border_fraction: float = BORDER_FRACTION,
):
    if height <= 0 or width <= 0:
        raise ValueError(
            "Image dimensions must be positive."
        )

    if not 0.0 <= border_fraction < 0.5:
        raise ValueError(
            "border_fraction must be between 0 and 0.5."
        )

    border_y = int(
        round(height * border_fraction)
    )

    border_x = int(
        round(width * border_fraction)
    )

    top = border_y
    bottom = height - border_y
    left = border_x
    right = width - border_x

    if bottom <= top or right <= left:
        raise ValueError(
            "Crop removed the entire image."
        )

    return top, bottom, left, right


def crop_rdsm(
    rdsm: np.ndarray,
    border_fraction: float = BORDER_FRACTION,
):
    if rdsm.ndim != 2:
        raise ValueError(
            f"Expected 2D rDSM, got {rdsm.shape}"
        )

    height, width = rdsm.shape

    top, bottom, left, right = (
        calculate_crop_bounds(
            height,
            width,
            border_fraction,
        )
    )

    cropped = rdsm[
        top:bottom,
        left:right,
    ].copy()

    return cropped, (
        top,
        bottom,
        left,
        right,
    )


def clean_rdsm(rdsm: np.ndarray):
    rdsm = np.asarray(
        rdsm,
        dtype=np.float32,
    ).copy()

    finite_mask = np.isfinite(rdsm)

    if not finite_mask.any():
        raise ValueError(
            "rDSM contains no finite values."
        )

    finite_values = rdsm[finite_mask]

    median_value = float(
        np.median(finite_values)
    )

    rdsm[~finite_mask] = median_value

    return rdsm


def stabilize_mesh_boundary(
    mesh_z: np.ndarray,
):
    if mesh_z.shape[0] < 3 or mesh_z.shape[1] < 3:
        return mesh_z

    result = mesh_z.copy()

    # Replace the outermost row and column
    # with their immediate interior values.
    result[0, :] = result[1, :]
    result[-1, :] = result[-2, :]

    result[:, 0] = result[:, 1]
    result[:, -1] = result[:, -2]

    return result


def prepare_mesh_z(
    rdsm: np.ndarray,
    mesh_size: int = MESH_SIZE,
    border_fraction: float = BORDER_FRACTION,
):
    if mesh_size < 2:
        raise ValueError(
            "mesh_size must be at least 2."
        )

    print("\nPreparing rDSM for mesh...")
    print(
        f"Original rDSM shape: {rdsm.shape}"
    )

    rdsm = clean_rdsm(rdsm)

    cropped_rdsm, crop_bounds = crop_rdsm(
        rdsm,
        border_fraction,
    )

    top, bottom, left, right = crop_bounds

    print("\nBoundary crop:")
    print(f"  Top    : {top} px")
    print(
        f"  Bottom : {rdsm.shape[0] - bottom} px"
    )
    print(f"  Left   : {left} px")
    print(
        f"  Right  : {rdsm.shape[1] - right} px"
    )

    print(
        f"Cropped rDSM shape: {cropped_rdsm.shape}"
    )

    crop_h, crop_w = cropped_rdsm.shape

    row_indices = np.linspace(
        0,
        crop_h - 1,
        mesh_size,
    ).astype(np.int32)

    col_indices = np.linspace(
        0,
        crop_w - 1,
        mesh_size,
    ).astype(np.int32)

    mesh_z = cropped_rdsm[
        np.ix_(
            row_indices,
            col_indices,
        )
    ].astype(np.float32)

    if STABILIZE_BOUNDARY:
        mesh_z = stabilize_mesh_boundary(
            mesh_z
        )

    mesh_z *= VERTICAL_EXAGGERATION

    z_offset = float(
        np.min(mesh_z)
    )

    mesh_z -= z_offset

    print("\nMesh elevation range:")
    print(
        f"  {mesh_z.min():.6f} → "
        f"{mesh_z.max():.6f} m"
    )

    print(
        f"Z offset: {z_offset:.6f} m"
    )

    return mesh_z, crop_bounds


def create_vertices(
    mesh_z: np.ndarray,
):
    mesh_height, mesh_width = mesh_z.shape

    vertices = []

    for row in range(mesh_height):
        for col in range(mesh_width):

            x = (
                col
                * X_SPACING
            )

            y = (
                mesh_height
                - 1
                - row
            ) * Y_SPACING

            z = float(
                mesh_z[row, col]
            )

            vertices.append(
                (
                    x,
                    y,
                    z,
                )
            )

    return vertices


def create_faces(
    mesh_size: int = MESH_SIZE,
):
    faces = []

    for row in range(mesh_size - 1):
        for col in range(mesh_size - 1):

            top_left = (
                row
                * mesh_size
                + col
            )

            top_right = top_left + 1

            bottom_left = (
                (row + 1)
                * mesh_size
                + col
            )

            bottom_right = bottom_left + 1

            faces.append(
                (
                    top_left,
                    bottom_left,
                    top_right,
                )
            )

            faces.append(
                (
                    top_right,
                    bottom_left,
                    bottom_right,
                )
            )

    return faces


def generate_mesh(
    metric_rdsm_path,
    scene_name: str,
):
    metric_rdsm_path = Path(
        metric_rdsm_path
    )

    if not metric_rdsm_path.exists():
        raise FileNotFoundError(
            f"Metric rDSM not found:\n"
            f"{metric_rdsm_path}"
        )

    print("=" * 75)
    print(
        "GEOSCULPT - TERRAIN MESH GENERATION"
    )
    print("=" * 75)

    rdsm = np.load(
        metric_rdsm_path
    ).astype(np.float32)

    print(
        f"\nInput shape: {rdsm.shape}"
    )

    print(
        f"Input range: "
        f"{np.nanmin(rdsm):.6f} → "
        f"{np.nanmax(rdsm):.6f} m"
    )

    mesh_z, crop_bounds = prepare_mesh_z(
        rdsm
    )

    vertices = create_vertices(
        mesh_z
    )

    faces = create_faces(
        MESH_SIZE
    )

    output_obj = (
        RESULTS_DIR
        / f"{scene_name}_terrain.obj"
    )

    with open(
        output_obj,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            "# GeoSculpt terrain mesh\n"
        )

        f.write(
            f"# Scene: {scene_name}\n"
        )

        f.write(
            f"# Mesh resolution: "
            f"{MESH_SIZE} x {MESH_SIZE}\n"
        )

        f.write(
            f"# Border crop: "
            f"{BORDER_FRACTION * 100:.2f}%\n"
        )

        for x, y, z in vertices:
            f.write(
                f"v {x:.6f} "
                f"{y:.6f} "
                f"{z:.6f}\n"
            )

        for v1, v2, v3 in faces:
            f.write(
                f"f {v1 + 1} "
                f"{v2 + 1} "
                f"{v3 + 1}\n"
            )

    print(
        "\nMesh generation complete."
    )

    print(
        f"Vertices : {len(vertices):,}"
    )

    print(
        f"Faces    : {len(faces):,}"
    )

    print(
        f"OBJ      : {output_obj}"
    )

    return {
        "obj_path": output_obj,
        "vertices": len(vertices),
        "faces": len(faces),
        "mesh_size": MESH_SIZE,
        "crop_bounds": crop_bounds,
    }


if __name__ == "__main__":

    test_rdsm = (
        ROOT
        / "results"
        / "depth"
        / "test_metric_rDSM.npy"
    )

    if not test_rdsm.exists():
        print(
            "Test rDSM not found:"
        )
        print(test_rdsm)
        print(
            "\nRun depth_inference.py first."
        )
    else:
        result = generate_mesh(
            test_rdsm,
            "test",
        )

        print("\nTEST SUCCESS")
        print(result)