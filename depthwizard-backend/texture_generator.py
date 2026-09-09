from pathlib import Path

import numpy as np
from PIL import Image


# ============================================================
# Configuration
# ============================================================

ROOT = Path(__file__).resolve().parent

RESULTS_DIR = (
    ROOT
    / "results"
    / "mesh"
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

MESH_SIZE = 256

X_SPACING = 1.0
Y_SPACING = 1.0

VERTICAL_EXAGGERATION = 35.0

# Remove 4% from every image edge.
BORDER_FRACTION = 0.04


# ============================================================
# Utility: calculate crop bounds
# ============================================================

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

    if (
        bottom <= top
        or right <= left
    ):
        raise ValueError(
            "Crop removed the entire image."
        )

    return (
        top,
        bottom,
        left,
        right,
    )


# ============================================================
# Utility: clean rDSM
# ============================================================

def clean_rdsm(
    rdsm: np.ndarray,
):
    rdsm = np.asarray(
        rdsm,
        dtype=np.float32,
    ).copy()

    finite_mask = np.isfinite(
        rdsm
    )

    if not finite_mask.any():
        raise ValueError(
            "rDSM contains no finite values."
        )

    finite_values = rdsm[
        finite_mask
    ]

    median_value = float(
        np.median(
            finite_values
        )
    )

    rdsm[
        ~finite_mask
    ] = median_value

    return rdsm


# ============================================================
# Utility: stabilize mesh boundary
# ============================================================

def stabilize_mesh_boundary(
    mesh_z: np.ndarray,
):
    if mesh_z.ndim != 2:
        raise ValueError(
            "mesh_z must be 2D."
        )

    if (
        mesh_z.shape[0] < 3
        or mesh_z.shape[1] < 3
    ):
        return mesh_z

    result = mesh_z.copy()

    # Replace outermost rows with
    # the immediately inner rows.
    result[0, :] = result[1, :]
    result[-1, :] = result[-2, :]

    # Replace outermost columns with
    # the immediately inner columns.
    result[:, 0] = result[:, 1]
    result[:, -1] = result[:, -2]

    return result


# ============================================================
# Load RGB image
# ============================================================

def load_rgb_image(
    image_path,
):
    image_path = Path(
        image_path
    )

    if not image_path.exists():
        raise FileNotFoundError(
            f"RGB image not found:\n"
            f"{image_path}"
        )

    try:
        image = Image.open(
            image_path
        ).convert("RGB")

    except Exception as exc:
        raise ValueError(
            f"Could not open RGB image: {exc}"
        )

    return image


# ============================================================
# Crop RGB image
# ============================================================

def crop_rgb_image(
    image: Image.Image,
):
    width, height = image.size

    top, bottom, left, right = (
        calculate_crop_bounds(
            height,
            width,
            BORDER_FRACTION,
        )
    )

    cropped = image.crop(
        (
            left,
            top,
            right,
            bottom,
        )
    )

    return (
        cropped,
        (
            top,
            bottom,
            left,
            right,
        ),
    )


# ============================================================
# Prepare rDSM for mesh
# ============================================================

def prepare_mesh_z(
    rdsm: np.ndarray,
):
    if rdsm.ndim != 2:
        raise ValueError(
            f"Expected 2D rDSM, got {rdsm.shape}"
        )

    rdsm = clean_rdsm(
        rdsm
    )

    height, width = rdsm.shape

    top, bottom, left, right = (
        calculate_crop_bounds(
            height,
            width,
            BORDER_FRACTION,
        )
    )

    cropped = rdsm[
        top:bottom,
        left:right,
    ].copy()

    crop_height, crop_width = (
        cropped.shape
    )

    print(
        f"\nOriginal rDSM shape:"
        f" {height} × {width}"
    )

    print(
        f"Cropped rDSM shape:"
        f" {crop_height} × {crop_width}"
    )

    print(
        "\nBorder crop:"
    )

    print(
        f"  Top    : {top} px"
    )

    print(
        f"  Bottom : {height - bottom} px"
    )

    print(
        f"  Left   : {left} px"
    )

    print(
        f"  Right  : {width - right} px"
    )

    # --------------------------------------------------------
    # Downsample cropped rDSM
    # --------------------------------------------------------

    row_indices = np.linspace(
        0,
        crop_height - 1,
        MESH_SIZE,
    ).astype(
        np.int32
    )

    col_indices = np.linspace(
        0,
        crop_width - 1,
        MESH_SIZE,
    ).astype(
        np.int32
    )

    mesh_z = cropped[
        np.ix_(
            row_indices,
            col_indices,
        )
    ].astype(
        np.float32
    )

    # --------------------------------------------------------
    # Stabilize only the final mesh boundary
    # --------------------------------------------------------

    mesh_z = (
        stabilize_mesh_boundary(
            mesh_z
        )
    )

    # --------------------------------------------------------
    # Visualization-only vertical scaling
    # --------------------------------------------------------

    mesh_z *= (
        VERTICAL_EXAGGERATION
    )

    # --------------------------------------------------------
    # Shift minimum height to zero
    #
    # Source rDSM is not modified.
    # --------------------------------------------------------

    z_offset = float(
        np.min(mesh_z)
    )

    mesh_z -= z_offset

    print(
        "\nMesh elevation range:"
    )

    print(
        f"  {mesh_z.min():.6f}"
        f" → "
        f"{mesh_z.max():.6f} m"
    )

    print(
        f"Z offset: "
        f"{z_offset:.6f} m"
    )

    return (
        mesh_z,
        (
            top,
            bottom,
            left,
            right,
        ),
    )


# ============================================================
# Create vertices
# ============================================================

def create_vertices(
    mesh_z: np.ndarray,
):
    vertices = []

    for row in range(
        MESH_SIZE
    ):
        for col in range(
            MESH_SIZE
        ):
            x = (
                col
                * X_SPACING
            )

            y = (
                MESH_SIZE
                - 1
                - row
            ) * Y_SPACING

            z = float(
                mesh_z[
                    row,
                    col,
                ]
            )

            vertices.append(
                (
                    x,
                    y,
                    z,
                )
            )

    return vertices


# ============================================================
# Create UV coordinates
# ============================================================

def create_uvs():
    uvs = []

    for row in range(
        MESH_SIZE
    ):
        for col in range(
            MESH_SIZE
        ):
            u = (
                col
                / (
                    MESH_SIZE - 1
                )
            )

            v = 1.0 - (
                row
                / (
                    MESH_SIZE - 1
                )
            )

            uvs.append(
                (
                    u,
                    v,
                )
            )

    return uvs


# ============================================================
# Create triangular faces
# ============================================================

def create_faces():
    faces = []

    for row in range(
        MESH_SIZE - 1
    ):
        for col in range(
            MESH_SIZE - 1
        ):
            top_left = (
                row
                * MESH_SIZE
                + col
            )

            top_right = (
                top_left + 1
            )

            bottom_left = (
                (row + 1)
                * MESH_SIZE
                + col
            )

            bottom_right = (
                bottom_left + 1
            )

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


# ============================================================
# Write MTL
# ============================================================

def write_mtl(
    output_mtl,
    texture_filename,
):
    with open(
        output_mtl,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            "# GeoSculpt textured terrain material\n"
        )

        f.write(
            "newmtl TerrainMaterial\n"
        )

        f.write(
            "Ka 1.000000 1.000000 1.000000\n"
        )

        f.write(
            "Kd 1.000000 1.000000 1.000000\n"
        )

        f.write(
            "Ks 0.000000 0.000000 0.000000\n"
        )

        f.write(
            "d 1.000000\n"
        )

        f.write(
            "illum 1\n"
        )

        f.write(
            f"map_Kd {texture_filename}\n"
        )


# ============================================================
# Write OBJ
# ============================================================

def write_obj(
    output_obj,
    output_mtl,
    vertices,
    uvs,
    faces,
):
    with open(
        output_obj,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            "# GeoSculpt textured terrain\n"
        )

        f.write(
            "# Non-georeferenced mesh\n"
        )

        f.write(
            f"# Mesh resolution: "
            f"{MESH_SIZE} x {MESH_SIZE}\n"
        )

        f.write(
            f"# Border crop: "
            f"{BORDER_FRACTION * 100:.2f}%\n"
        )

        f.write(
            f"mtllib {output_mtl.name}\n"
        )

        f.write(
            "o GeoSculptTerrain\n"
        )

        f.write(
            "usemtl TerrainMaterial\n"
        )

        # ----------------------------------------------------
        # Vertices
        # ----------------------------------------------------

        for x, y, z in vertices:
            f.write(
                f"v {x:.6f} "
                f"{y:.6f} "
                f"{z:.6f}\n"
            )

        # ----------------------------------------------------
        # UV coordinates
        # ----------------------------------------------------

        for u, v in uvs:
            f.write(
                f"vt {u:.6f} "
                f"{v:.6f}\n"
            )

        # ----------------------------------------------------
        # Faces
        # ----------------------------------------------------

        for v1, v2, v3 in faces:

            a = v1 + 1
            b = v2 + 1
            c = v3 + 1

            f.write(
                f"f {a}/{a} "
                f"{b}/{b} "
                f"{c}/{c}\n"
            )


# ============================================================
# Main API function
# ============================================================

def generate_textured_mesh(
    image_path,
    metric_rdsm_path,
    scene_name,
):
    image_path = Path(
        image_path
    )

    metric_rdsm_path = Path(
        metric_rdsm_path
    )

    print(
        "\n" + "=" * 75
    )

    print(
        "GEOSCULPT - TEXTURED TERRAIN GENERATION"
    )

    print(
        "=" * 75
    )

    # --------------------------------------------------------
    # Validate inputs
    # --------------------------------------------------------

    if not image_path.exists():
        raise FileNotFoundError(
            f"RGB image not found:\n"
            f"{image_path}"
        )

    if not metric_rdsm_path.exists():
        raise FileNotFoundError(
            f"Metric rDSM not found:\n"
            f"{metric_rdsm_path}"
        )

    print(
        f"\nRGB image:\n"
        f"{image_path}"
    )

    print(
        f"\nMetric rDSM:\n"
        f"{metric_rdsm_path}"
    )

    # --------------------------------------------------------
    # Load RGB
    # --------------------------------------------------------

    image = load_rgb_image(
        image_path
    )

    rgb_width, rgb_height = (
        image.size
    )

    print(
        f"\nRGB size: "
        f"{rgb_width} × {rgb_height}"
    )

    # --------------------------------------------------------
    # Load rDSM
    # --------------------------------------------------------

    rdsm = np.load(
        metric_rdsm_path
    ).astype(
        np.float32
    )

    print(
        f"rDSM shape: "
        f"{rdsm.shape}"
    )

    if (
        rdsm.shape[0]
        != rgb_height
        or
        rdsm.shape[1]
        != rgb_width
    ):
        raise ValueError(
            "RGB and rDSM dimensions do not match:\n"
            f"RGB  : "
            f"{rgb_height} × {rgb_width}\n"
            f"rDSM : "
            f"{rdsm.shape[0]} × "
            f"{rdsm.shape[1]}"
        )

    # --------------------------------------------------------
    # Crop RGB
    # --------------------------------------------------------

    cropped_image, rgb_crop_bounds = (
        crop_rgb_image(
            image
        )
    )

    # --------------------------------------------------------
    # Prepare rDSM
    # --------------------------------------------------------

    mesh_z, rdsm_crop_bounds = (
        prepare_mesh_z(
            rdsm
        )
    )

    # --------------------------------------------------------
    # Make sure RGB and rDSM use
    # exactly the same crop.
    # --------------------------------------------------------

    if (
        rgb_crop_bounds
        != rdsm_crop_bounds
    ):
        raise RuntimeError(
            "RGB and rDSM crop bounds do not match."
        )

    top, bottom, left, right = (
        rgb_crop_bounds
    )

    print(
        "\nShared crop bounds:"
    )

    print(
        f"  top    = {top}"
    )

    print(
        f"  bottom = {bottom}"
    )

    print(
        f"  left   = {left}"
    )

    print(
        f"  right  = {right}"
    )

    # --------------------------------------------------------
    # Save cropped RGB texture
    # --------------------------------------------------------

    output_texture = (
        RESULTS_DIR
        / f"{scene_name}_texture.png"
    )

    cropped_image.save(
        output_texture
    )

    print(
        f"\nTexture saved:\n"
        f"{output_texture}"
    )

    # --------------------------------------------------------
    # Create geometry
    # --------------------------------------------------------

    print(
        "\nCreating vertices..."
    )

    vertices = (
        create_vertices(
            mesh_z
        )
    )

    print(
        "Creating UV coordinates..."
    )

    uvs = create_uvs()

    print(
        "Creating triangular faces..."
    )

    faces = create_faces()

    # --------------------------------------------------------
    # Output filenames
    # --------------------------------------------------------

    output_obj = (
        RESULTS_DIR
        / f"{scene_name}_textured.obj"
    )

    output_mtl = (
        RESULTS_DIR
        / f"{scene_name}_textured.mtl"
    )

    # --------------------------------------------------------
    # Write MTL
    # --------------------------------------------------------

    print(
        "Writing MTL..."
    )

    write_mtl(
        output_mtl,
        output_texture.name,
    )

    # --------------------------------------------------------
    # Write OBJ
    # --------------------------------------------------------

    print(
        "Writing OBJ..."
    )

    write_obj(
        output_obj,
        output_mtl,
        vertices,
        uvs,
        faces,
    )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print(
        "\n" + "=" * 75
    )

    print(
        "TEXTURED TERRAIN GENERATION COMPLETE"
    )

    print(
        "=" * 75
    )

    print(
        f"\nVertices : "
        f"{len(vertices):,}"
    )

    print(
        f"UVs      : "
        f"{len(uvs):,}"
    )

    print(
        f"Faces    : "
        f"{len(faces):,}"
    )

    print(
        f"\nOBJ:\n"
        f"{output_obj}"
    )

    print(
        f"\nMTL:\n"
        f"{output_mtl}"
    )

    print(
        f"\nTexture:\n"
        f"{output_texture}"
    )

    return {
        "obj_path": output_obj,
        "mtl_path": output_mtl,
        "texture_path": output_texture,
        "vertices": len(vertices),
        "uvs": len(uvs),
        "faces": len(faces),
        "mesh_size": MESH_SIZE,
        "crop_bounds": rgb_crop_bounds,
    }


# ============================================================
# Standalone test
# ============================================================

if __name__ == "__main__":

    test_image = (
        ROOT
        / "uploads"
        / "test.jpg"
    )

    test_rdsm = (
        ROOT
        / "results"
        / "depth"
        / "test_metric_rDSM.npy"
    )

    if (
        not test_image.exists()
        or not test_rdsm.exists()
    ):
        print(
            "Standalone test files not found."
        )

        print(
            f"\nImage:\n"
            f"{test_image}"
        )

        print(
            f"\nrDSM:\n"
            f"{test_rdsm}"
        )

        print(
            "\nRun depth_inference.py first."
        )

    else:

        result = generate_textured_mesh(
            test_image,
            test_rdsm,
            "test",
        )

        print(
            "\nTEST SUCCESS"
        )

        print(
            result
        )