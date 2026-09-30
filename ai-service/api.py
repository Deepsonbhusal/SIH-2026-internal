from pathlib import Path
import shutil
import subprocess
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException

app = FastAPI(title="GeoSculpt AI Service", version="0.1.0")

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
CHECKPOINT = Path(
    r"C:\Users\Dipson\dept-wizard\depthwizard-backend"
    r"\outputs\finetune_v3\checkpoints\best.pth"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
def health():
    return {
        "service": "GeoSculpt AI",
        "status": "ready",
    }


@app.post("/process")
async def process(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No file provided")

    job_id = f"{Path(file.filename).stem}_{uuid.uuid4().hex[:8]}"

    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    input_path = job_dir / Path(file.filename).name

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

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
            text=True,
        )

        if result.returncode != 0:
            raise HTTPException(
                500,
                {
                    "status": "failed",
                    "error": result.stderr[-4000:],
                },
            )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(500, str(exc))

    scene_dir = job_dir / Path(file.filename).stem

    return {
        "status": "success",
        "job_id": job_id,
        "output_dir": str(scene_dir),
        "stdout": result.stdout[-2000:],
    }