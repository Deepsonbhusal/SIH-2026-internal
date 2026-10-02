from pathlib import Path
from uuid import uuid4
import shutil
import subprocess

import cv2
import numpy as np
import rasterio
import requests

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="GeoSculpt Backend",
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://deepsonbhusal.github.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DIRECTORIES
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads"
RESULTS_DIR = BASE_DIR / "results"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# AI SERVICE
# =========================================================

AI_SERVICE_URL = (
    "https://sih-2026-internal-1.onrender.com/process"
)


# =========================================================
# STATIC RESULTS
# =========================================================

app.mount(
    "/results",
    StaticFiles(directory=str(RESULTS_DIR)),
    name="results",
)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
def health_check():

    return {
        "message": "GeoSculpt backend is running",
        "pipeline": "GeoSculpt AI Service",
        "status": "ready",
        "ai_service": AI_SERVICE_URL,
    }


# =========================================================
# CREATE DEPTH PREVIEW
# =========================================================

def create_depth_preview(
    scene_dir: Path,
):

    inference_dir = scene_dir / "inference"

    tif_path = (
        inference_dir
        / "relative_dsm.tif"
    )

    preview_path = (
        inference_dir
        / "relative_dsm_preview.png"
    )

    if not tif_path.exists():

        raise FileNotFoundError(
            "relative_dsm.tif was not found."
        )

    print(
        "Creating depth preview..."
    )

    with rasterio.open(tif_path) as src:

        depth = src.read(1)

    depth = np.nan_to_num(
        depth,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    ).astype(
        np.float32
    )

    low, high = np.percentile(
        depth,
        [2, 98],
    )

    normalized = (
        depth - low
    ) / (
        high - low + 1e-8
    )

    normalized = np.clip(
        normalized,
        0.0,
        1.0,
    )

    preview = (
        normalized * 255.0
    ).astype(
        np.uint8
    )

    cv2.imwrite(
        str(preview_path),
        preview,
    )

    print(
        "Depth preview:",
        preview_path,
    )

    return preview_path


# =========================================================
# CREATE TERRAIN MESH
# =========================================================

def create_terrain_mesh(
    scene_dir: Path,
    input_image: Path,
):

    """
    Create a textured relative-depth terrain OBJ.

    This is a visualization mesh.

    It is NOT a metric DSM.

    The current pipeline uses monocular relative depth,
    so the vertical scale is intentionally conservative.
    """

    inference_dir = (
        scene_dir / "inference"
    )

    tif_path = (
        inference_dir
        / "relative_dsm.tif"
    )

    if not tif_path.exists():

        raise FileNotFoundError(
            "relative_dsm.tif was not found."
        )

    terrain_dir = (
        scene_dir / "terrain"
    )

    terrain_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    obj_path = (
        terrain_dir
        / "terrain.obj"
    )

    texture_path = (
        terrain_dir
        / "texture.jpg"
    )

    print(
        "Creating terrain mesh..."
    )

    # =====================================================
    # READ DEPTH
    # =====================================================

    with rasterio.open(tif_path) as src:

        depth = src.read(1)

    depth = np.nan_to_num(
        depth,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    ).astype(
        np.float32
    )

    # =====================================================
    # REDUCE MESH RESOLUTION
    # =====================================================

    rows = 160
    cols = 240

    depth = cv2.resize(
        depth,
        (
            cols,
            rows,
        ),
        interpolation=cv2.INTER_AREA,
    )

    # =====================================================
    # REMOVE EXTREME OUTLIERS
    # =====================================================

    low, high = np.percentile(
        depth,
        [2, 98],
    )

    depth = np.clip(
        depth,
        low,
        high,
    )

    # =====================================================
    # NORMALIZE
    # =====================================================

    depth = (
        depth - low
    ) / (
        high - low + 1e-8
    )

    depth = np.clip(
        depth,
        0.0,
        1.0,
    )

    # =====================================================
    # SMOOTH DEPTH
    # =====================================================

    depth = cv2.GaussianBlur(
        depth,
        (0, 0),
        sigmaX=1.2,
        sigmaY=1.2,
    )

    # =====================================================
    # SUPPRESS LOW-LEVEL DEPTH NOISE
    # =====================================================

    depth = np.clip(
        (depth - 0.30) / 0.70,
        0.0,
        1.0,
    )

    # =====================================================
    # HEIGHT CURVE
    # =====================================================

    depth = np.power(
        depth,
        2.0,
    )

    # =====================================================
    # FINAL VERTICAL SCALE
    # =====================================================

    depth *= 5.0

    depth = np.clip(
        depth,
        0.0,
        5.0,
    )

    # =====================================================
    # CREATE TEXTURE
    # =====================================================

    image = Image.open(
        input_image
    ).convert(
        "RGB"
    )

    image.save(
        texture_path,
        "JPEG",
        quality=90,
    )

    # =====================================================
    # TERRAIN DIMENSIONS
    # =====================================================

    terrain_width = 100.0
    terrain_depth = 65.0

    # =====================================================
    # WRITE OBJ
    # =====================================================

    with open(
        obj_path,
        "w",
        encoding="utf-8",
    ) as obj:

        obj.write(
            "# GeoSculpt relative-depth terrain\n"
        )

        obj.write(
            "# Visualization mesh only\n"
        )

        # -------------------------------------------------
        # VERTICES
        # -------------------------------------------------

        for y in range(rows):

            for x in range(cols):

                px = (
                    x /
                    (cols - 1)
                )

                py = (
                    y /
                    (rows - 1)
                )

                world_x = (
                    px - 0.5
                ) * terrain_width

                world_y = (
                    0.5 - py
                ) * terrain_depth

                world_z = float(
                    depth[y, x]
                )

                obj.write(
                    f"v "
                    f"{world_x:.5f} "
                    f"{world_z:.5f} "
                    f"{world_y:.5f}\n"
                )

        # -------------------------------------------------
        # UV COORDINATES
        # -------------------------------------------------

        for y in range(rows):

            for x in range(cols):

                u = (
                    x /
                    (cols - 1)
                )

                v = 1.0 - (
                    y /
                    (rows - 1)
                )

                obj.write(
                    f"vt "
                    f"{u:.6f} "
                    f"{v:.6f}\n"
                )

        # -------------------------------------------------
        # TRIANGLES
        # -------------------------------------------------

        for y in range(rows - 1):

            for x in range(cols - 1):

                a = (
                    y * cols
                    + x
                    + 1
                )

                b = (
                    y * cols
                    + x
                    + 2
                )

                c = (
                    (y + 1) * cols
                    + x
                    + 2
                )

                d = (
                    (y + 1) * cols
                    + x
                    + 1
                )

                # Triangle 1

                obj.write(
                    f"f "
                    f"{a}/{a} "
                    f"{b}/{b} "
                    f"{c}/{c}\n"
                )

                # Triangle 2

                obj.write(
                    f"f "
                    f"{a}/{a} "
                    f"{c}/{c} "
                    f"{d}/{d}\n"
                )

    print(
        "Terrain OBJ:",
        obj_path,
    )

    print(
        "Terrain texture:",
        texture_path,
    )

    return (
        obj_path,
        texture_path,
    )


# =========================================================
# PROCESS IMAGE
# =========================================================

@app.post("/process")
async def process_image_api(
    file: UploadFile = File(...),
    image_type: str = Form(...),
    latitude: str = Form(""),
    longitude: str = Form(""),
    dem_file: UploadFile | None = File(None),
):

    # =====================================================
    # VALIDATE
    # =====================================================

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No image filename provided.",
        )

    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".tif",
        ".tiff",
    }

    original_filename = Path(
        file.filename
    ).name

    extension = Path(
        original_filename
    ).suffix.lower()

    if extension not in allowed_extensions:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported image format. "
                "Use JPG, PNG, TIFF, or TIF."
            ),
        )

    # =====================================================
    # CURRENT PIPELINE
    # =====================================================

    if image_type != "normal":

        raise HTTPException(
            status_code=400,
            detail=(
                "Georeferenced processing is "
                "not connected yet. "
                "Use the non-georeferenced "
                "image type for now."
            ),
        )

    # =====================================================
    # UNIQUE SCENE NAME
    # =====================================================

    unique_id = uuid4().hex[:8]

    original_stem = Path(
        original_filename
    ).stem

    scene_name = (
        f"{original_stem}_"
        f"{unique_id}"
    )

    input_filename = (
        f"{scene_name}"
        f"{extension}"
    )

    input_path = (
        UPLOAD_DIR
        / input_filename
    )

    # =====================================================
    # SAVE UPLOAD
    # =====================================================

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
                "Failed to save uploaded image: "
                f"{exc}"
            ),
        )

    # =====================================================
    # DEM FILE
    # =====================================================

    if dem_file is not None:

        print(
            "DEM file received."
        )

        print(
            "DEM processing will be connected "
            "in the georeferenced pipeline."
        )

    # =====================================================
    # LOG
    # =====================================================

    print("")
    print("=" * 75)
    print("GEOSCULPT - API PROCESSING")
    print("=" * 75)

    print(
        "Input image :",
        original_filename,
    )

    print(
        "Scene name  :",
        scene_name,
    )

    print(
        "AI service  :",
        AI_SERVICE_URL,
    )

    # =====================================================
    # CALL AI SERVICE
    # =====================================================

    try:

        with open(
            input_path,
            "rb",
        ) as image_file:

            response = requests.post(
                AI_SERVICE_URL,
                files={
                    "file": (
                        original_filename,
                        image_file,
                        file.content_type
                        or "application/octet-stream",
                    )
                },
                timeout=1800,
            )

        # =================================================
        # IMPORTANT DEBUG LOGGING
        # =================================================

        print(
            "AI STATUS:",
            response.status_code,
        )

        print(
            "AI RESPONSE:",
            response.text[:10000],
        )

        # =================================================
        # CHECK HTTP STATUS
        # =================================================

        response.raise_for_status()

        ai_result = response.json()

    except requests.exceptions.ConnectionError as exc:

        print(
            "AI CONNECTION ERROR:",
            str(exc),
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "GeoSculpt AI service connection failed: "
                f"{exc}"
            ),
        )

    except requests.exceptions.Timeout as exc:

        print(
            "AI TIMEOUT:",
            str(exc),
        )

        raise HTTPException(
            status_code=504,
            detail=(
                "GeoSculpt AI service timed out "
                "while processing the image."
            ),
        )

    except requests.exceptions.HTTPError:

        print(
            "AI HTTP ERROR:",
            response.status_code,
        )

        print(
            "AI ERROR BODY:",
            response.text[:10000],
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "GeoSculpt AI service failed: "
                f"{response.text}"
            ),
        )

    except Exception as exc:

        print(
            "AI COMMUNICATION ERROR:",
            str(exc),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to communicate with "
                "GeoSculpt AI service: "
                f"{exc}"
            ),
        )

    # =====================================================
    # CHECK AI RESULT
    # =====================================================

    if ai_result.get("status") != "success":

        raise HTTPException(
            status_code=500,
            detail={
                "message": "AI processing failed.",
                "ai_result": ai_result,
            },
        )

    print("")
    print(
        "GeoSculpt AI processing completed."
    )

    print(
        "AI job ID:",
        ai_result.get("job_id"),
    )

    print(
        "AI output:",
        ai_result.get("output_dir"),
    )

    # =====================================================
    # AI OUTPUT DIRECTORY
    # =====================================================

    ai_output_dir = ai_result.get(
        "output_dir"
    )

    if not ai_output_dir:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI service completed but "
                "did not return an output directory."
            ),
        )

    ai_output_path = Path(
        ai_output_dir
    )

    if not ai_output_path.exists():

        raise HTTPException(
            status_code=500,
            detail=(
                "AI service returned an output "
                "directory that does not exist."
            ),
        )

    # =====================================================
    # BACKEND RESULT DIRECTORY
    # =====================================================

    backend_result_dir = (
        RESULTS_DIR
        / scene_name
    )

    try:

        if backend_result_dir.exists():

            shutil.rmtree(
                backend_result_dir
            )

        shutil.copytree(
            ai_output_path,
            backend_result_dir,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI output was generated, "
                "but copying the results failed: "
                f"{exc}"
            ),
        )

    # =====================================================
    # CREATE PREVIEW
    # =====================================================

    try:

        create_depth_preview(
            backend_result_dir
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Depth preview generation failed: "
                f"{exc}"
            ),
        )

    # =====================================================
    # CREATE TERRAIN
    # =====================================================

    try:

        obj_path, texture_path = (
            create_terrain_mesh(
                backend_result_dir,
                input_path,
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Terrain generation failed: "
                f"{exc}"
            ),
        )

    # =====================================================
    # GENERATED FILES
    # =====================================================

    generated_files = []

    for path in backend_result_dir.rglob("*"):

        if path.is_file():

            try:

                relative = (
                    path.relative_to(
                        backend_result_dir
                    )
                )

                generated_files.append(
                    str(relative)
                )

            except Exception:

                pass

    generated_files.sort()

    # =====================================================
    # URLS
    # =====================================================

    depth_url = (
        f"/results/"
        f"{scene_name}/"
        f"inference/"
        f"relative_dsm_preview.png"
    )

    obj_url = (
        f"/results/"
        f"{scene_name}/"
        f"terrain/"
        f"terrain.obj"
    )

    texture_url = (
        f"/results/"
        f"{scene_name}/"
        f"terrain/"
        f"texture.jpg"
    )

    scene_meta_url = (
        f"/results/"
        f"{scene_name}/"
        f"meta/"
        f"scene_meta.json"
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    return {
        "status": "success",

        "filename": original_filename,

        "scene_name": scene_name,

        "image_type": image_type,

        "pipeline": "GeoSculpt AI Service",

        "job_id": ai_result.get(
            "job_id"
        ),

        # -------------------------------------------------
        # AI OUTPUT
        # -------------------------------------------------

        "ai_output": {

            "output_dir": str(
                backend_result_dir
            ),

            "relative_dsm_url": depth_url,

            "terrain_obj_url": obj_url,

            "terrain_texture_url": texture_url,

            "scene_meta_url": scene_meta_url,

            "generated_files": generated_files,
        },

        # -------------------------------------------------
        # FRONTEND COMPATIBILITY
        # -------------------------------------------------

        "relative_rdsm": {

            "png_url": depth_url,

        },

        "mesh": {

            "obj_url": obj_url,

            "texture_url": texture_url,

        },

        "terrain_obj_url": obj_url,

        "terrain_texture_url": texture_url,

        # -------------------------------------------------
        # LOCATION
        # -------------------------------------------------

        "location": {

            "latitude": latitude,

            "longitude": longitude,

        },

        # -------------------------------------------------
        # INFO
        # -------------------------------------------------

        "message": (
            "Image successfully processed "
            "by the GeoSculpt AI service."
        ),
    }