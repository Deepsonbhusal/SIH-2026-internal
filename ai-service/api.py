from pathlib import Path
import shutil
import subprocess
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException


app = FastAPI(
    title="GeoSculpt AI Service",
    version="0.1.0"
)


ROOT = Path(__file__).resolve().parent

OUTPUT_DIR = ROOT / "outputs"

CHECKPOINT = ROOT / "models" / "best.pth"


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


@app.get("/")
def health():
    return {
        "service": "GeoSculpt AI",
        "status": "ready"
    }


@app.post("/process")
async def process(
    file: UploadFile = File(...)
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file provided"
        )


    # ---------------------------------------------------------
    # Create unique job directory
    # ---------------------------------------------------------

    original_name = Path(
        file.filename
    ).name

    file_stem = Path(
        original_name
    ).stem

    job_id = (
        f"{file_stem}_"
        f"{uuid.uuid4().hex[:8]}"
    )

    job_dir = OUTPUT_DIR / job_id

    job_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    # ---------------------------------------------------------
    # Save uploaded image
    # ---------------------------------------------------------

    input_path = job_dir / original_name

    try:

        with open(
            input_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded file: {exc}"
        )


    # ---------------------------------------------------------
    # Check model checkpoint
    # ---------------------------------------------------------

    if not CHECKPOINT.exists():

        raise HTTPException(
            status_code=500,
            detail=(
                "Model checkpoint not found: "
                f"{CHECKPOINT}"
            )
        )


    # ---------------------------------------------------------
    # Run GeoSculpt AI pipeline
    # ---------------------------------------------------------

    command = [
        "python",
        "-m",
        "src.dw.core.run",

        "--input",
        str(input_path),

        "--output-dir",
        str(job_dir),

        "--checkpoint",
        str(CHECKPOINT),

        "--device",
        "cpu",

        "--no-fp16",
    ]


    try:

        result = subprocess.run(
            command,
            cwd=str(ROOT),
            capture_output=True,
            text=True
        )


        # -----------------------------------------------------
        # Pipeline failed
        # -----------------------------------------------------

        if result.returncode != 0:

            error_output = (
                result.stderr
                + "\n"
                + result.stdout
            )[-8000:]

            raise HTTPException(
                status_code=500,
                detail={
                    "status": "failed",
                    "error": error_output
                }
            )


    except HTTPException:

        raise


    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )


    # ---------------------------------------------------------
    # Expected scene output directory
    # ---------------------------------------------------------

    scene_dir = (
        job_dir
        / file_stem
    )


    # ---------------------------------------------------------
    # Return result
    # ---------------------------------------------------------

    return {
        "status": "success",

        "job_id": job_id,

        "output_dir": str(
            scene_dir
        ),

        "stdout": result.stdout[-4000:],

        "stderr": result.stderr[-4000:]
    }