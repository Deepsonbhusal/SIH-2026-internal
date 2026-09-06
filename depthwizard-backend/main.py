from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image
import os
import shutil

app = FastAPI()

app.mount("/results", StaticFiles(directory="results"), name="results")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
os.makedirs("results", exist_ok=True)


@app.get("/")
def home():
    return {"message": "DepthWizard backend is running"}


@app.post("/process")
async def process_image(file: UploadFile = File(...)):

    # 1. Save uploaded image
    input_path = os.path.join("uploads", file.filename)

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Open the image
    image = Image.open(input_path).convert("L")

    # 3. Create a temporary dummy depth map
    depth_path = os.path.join("results", "depth.png")
    image.save(depth_path)

    # 4. Return result information
    return {
        "status": "success",
        "filename": file.filename,
        "depth_map_url": "http://localhost:8000/results/depth.png",
        "message": "Depth map generated successfully"
    }