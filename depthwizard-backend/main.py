from pathlib import Path
from uuid import uuid4
import shutil

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from fastapi.staticfiles import (
    StaticFiles,
)

from depth_inference import (
    process_image,
)

from texture_generator import (
    generate_textured_mesh,
)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="GeoSculpt Backend",
    version="1.0.0",
)


# ============================================================
# PATHS
# ============================================================

ROOT = Path(
    __file__
).resolve().parent

UPLOAD_DIR = (
    ROOT
    / "uploads"
)

RESULTS_DIR = (
    ROOT
    / "results"
)

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# STATIC RESULTS
# ============================================================

app.mount(
    "/results",
    StaticFiles(
        directory=str(
            RESULTS_DIR
        )
    ),
    name="results",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():

    return {
        "message":
            "GeoSculpt backend is running",

        "pipeline":
            "non-georeferenced",

        "status":
            "ready",
    }


# ============================================================
# PROCESS
# ============================================================

@app.post("/process")
async def process_image_api(

    file: UploadFile = File(...),

    image_type: str = Form(...),

    latitude: str = Form(""),

    longitude: str = Form(""),

    dem_file: UploadFile | None = File(None),
):

    # --------------------------------------------------------
    # Current implementation
    # --------------------------------------------------------

    if image_type != "normal":

        raise HTTPException(
            status_code=400,
            detail=(
                "Georeferenced processing is "
                "not implemented yet. "
                "Use the non-georeferenced "
                "image type."
            ),
        )

    # --------------------------------------------------------
    # Validate filename
    # --------------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail=(
                "No image filename provided."
            ),
        )

    # --------------------------------------------------------
    # Allowed formats
    # --------------------------------------------------------

    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".tif",
        ".tiff",
    }

    original_filename = (
        Path(
            file.filename
        ).name
    )

    extension = (
        Path(
            original_filename
        ).suffix.lower()
    )

    if extension not in allowed_extensions:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported image format. "
                "Use JPG, PNG, TIFF, or TIF."
            ),
        )

    # --------------------------------------------------------
    # Unique scene name
    # --------------------------------------------------------

    unique_id = (
        uuid4()
        .hex[:8]
    )

    original_stem = (
        Path(
            original_filename
        ).stem
    )

    scene_name = (
        f"{original_stem}_{unique_id}"
    )

    input_filename = (
        f"{scene_name}"
        f"{extension}"
    )

    input_path = (
        UPLOAD_DIR
        / input_filename
    )

    # --------------------------------------------------------
    # Save image
    # --------------------------------------------------------

    try:

        with open(
            input_path,
            "wb",
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to save "
                f"uploaded image: {exc}"
            ),
        )

    # --------------------------------------------------------
    # DEM is not currently used
    # --------------------------------------------------------

    if dem_file is not None:

        print(
            "DEM file received, but "
            "georeferenced processing "
            "is disabled."
        )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    print(
        "\n"
    )

    print(
        "=" * 75
    )

    print(
        "GEOSCULPT - API PROCESSING"
    )

    print(
        "=" * 75
    )

    print(
        f"Input image : "
        f"{original_filename}"
    )

    print(
        f"Scene name  : "
        f"{scene_name}"
    )

    # --------------------------------------------------------
    # Depth processing
    # --------------------------------------------------------

    try:

        depth_result = (
            process_image(
                input_path,
                scene_name=scene_name,
            )
        )

    except Exception as exc:

        print(
            "\nDepth processing failed."
        )

        print(exc)

        raise HTTPException(
            status_code=500,
            detail=(
                f"Depth processing failed: "
                f"{exc}"
            ),
        )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # For a non-georeferenced RGB input,
    # use the RELATIVE rDSM for visualization.
    #
    # Do NOT use the global metric baseline
    # as the primary mesh input.
    # --------------------------------------------------------

    relative_rdsm_path = (
        depth_result[
            "relative_npy"
        ]
    )

    try:

        mesh_result = (
            generate_textured_mesh(
                input_path,
                relative_rdsm_path,
                scene_name=scene_name,
            )
        )

    except Exception as exc:

        print(
            "\nMesh processing failed."
        )

        print(exc)

        raise HTTPException(
            status_code=500,
            detail=(
                f"Mesh processing failed: "
                f"{exc}"
            ),
        )

    # --------------------------------------------------------
    # URLs
    # --------------------------------------------------------

    relative_png_url = (
        f"/results/depth/"
        f"{scene_name}_relative.png"
    )

    relative_npy_url = (
        f"/results/depth/"
        f"{scene_name}_relative.npy"
    )

    raw_npy_url = (
        f"/results/depth/"
        f"{scene_name}_raw_depth.npy"
    )

    metric_rdsm_png_url = (
        f"/results/depth/"
        f"{scene_name}_metric_rDSM.png"
    )

    metric_rdsm_npy_url = (
        f"/results/depth/"
        f"{scene_name}_metric_rDSM.npy"
    )

    obj_url = (
        f"/results/mesh/"
        f"{scene_name}_textured.obj"
    )

    mtl_url = (
        f"/results/mesh/"
        f"{scene_name}_textured.mtl"
    )

    texture_url = (
        f"/results/mesh/"
        f"{scene_name}_texture.png"
    )

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    metric_info = None

    if depth_result[
        "metric_rdsm"
    ] is not None:

        metric = (
            depth_result[
                "metric_rdsm"
            ]
        )

        metric_info = {
            "min": float(
                metric.min()
            ),

            "max": float(
                metric.max()
            ),

            "npy_url":
                metric_rdsm_npy_url,

            "png_url":
                metric_rdsm_png_url,
        }

    return {

        "status":
            "success",

        "filename":
            original_filename,

        "scene_name":
            scene_name,

        "image_type":
            "normal",

        "pipeline":
            "non-georeferenced",

        "depth_shape": [
            int(
                depth_result[
                    "relative_depth"
                ].shape[0]
            ),

            int(
                depth_result[
                    "relative_depth"
                ].shape[1]
            ),
        ],

        # ----------------------------------------------------
        # PRIMARY OUTPUT
        # ----------------------------------------------------

        "relative_rdsm": {

            "min": float(
                depth_result[
                    "relative_depth"
                ].min()
            ),

            "max": float(
                depth_result[
                    "relative_depth"
                ].max()
            ),

            "npy_url":
                relative_npy_url,

            "png_url":
                relative_png_url,
        },

        # ----------------------------------------------------
        # OPTIONAL METRIC BASELINE
        # ----------------------------------------------------

        "metric_baseline":
            metric_info,

        # ----------------------------------------------------
        # RAW DEPTH
        # ----------------------------------------------------

        "raw_depth": {

            "npy_url":
                raw_npy_url,
        },

        # ----------------------------------------------------
        # MESH
        # ----------------------------------------------------

        "mesh": {

            "obj_url":
                obj_url,

            "mtl_url":
                mtl_url,

            "texture_url":
                texture_url,

            "vertices":
                mesh_result[
                    "vertices"
                ],

            "uvs":
                mesh_result[
                    "uvs"
                ],

            "faces":
                mesh_result[
                    "faces"
                ],

            "mesh_size":
                mesh_result[
                    "mesh_size"
                ],

            "height_source":
                "relative_rDSM",

            "coordinate_system":
                "non-georeferenced",
        },

        "message": (
            "Image processed successfully. "
            "Relative rDSM and textured "
            "3D terrain generated."
        ),
    }