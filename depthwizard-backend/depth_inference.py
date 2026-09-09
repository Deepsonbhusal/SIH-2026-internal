from pathlib import Path
import sys

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent

DEPTH_ANYTHING_DIR = (
    ROOT
    / "depth_anything_v2"
)

CHECKPOINT = (
    ROOT
    / "outputs"
    / "finetune_v3"
    / "checkpoints"
    / "best.pth"
)

CALIBRATION_FILE = (
    ROOT
    / "outputs"
    / "multiscene_calibration"
    / "global_calibration.npz"
)

OUTPUT_DIR = (
    ROOT
    / "results"
    / "depth"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# MODEL CONFIGURATION
# ============================================================

ENCODER = "vitb"

INPUT_SIZE = 518

MODEL_CONFIG = {
    "vitb": {
        "encoder": "vitb",
        "features": 128,
        "out_channels": [
            96,
            192,
            384,
            768,
        ],
    }
}


# ============================================================
# DEPTH REFINEMENT
# ============================================================

# Robust normalization range.
LOW_PERCENTILE = 2.0
HIGH_PERCENTILE = 98.0

# First remove tiny isolated spikes.
MEDIAN_KERNEL = 5

# Then smooth noise while preserving larger structures.
BILATERAL_DIAMETER = 7
BILATERAL_SIGMA_COLOR = 0.12
BILATERAL_SIGMA_SPACE = 7.0


# ============================================================
# GLOBAL CALIBRATION
# ============================================================

USE_GLOBAL_CALIBRATION = True

CLIP_METRIC_TO_ZERO = True


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


# ============================================================
# MODEL CACHE
# ============================================================

_model = None

_linear_slope = None
_linear_intercept = None


# ============================================================
# HEADER
# ============================================================

print("=" * 75)

print(
    "GEOSCULPT - DEPTH INFERENCE + rDSM"
)

print("=" * 75)

print(
    f"\nDevice     : {DEVICE}"
)

print(
    f"Encoder    : {ENCODER}"
)

print(
    f"Input size : {INPUT_SIZE}"
)


# ============================================================
# IMPORT DEPTH ANYTHING V2
# ============================================================

if not DEPTH_ANYTHING_DIR.exists():
    raise FileNotFoundError(
        "Depth Anything V2 directory not found:\n"
        f"{DEPTH_ANYTHING_DIR}"
    )

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )

from depth_anything_v2.dpt import (
    DepthAnythingV2,
)


# ============================================================
# LOAD MODEL
# ============================================================

def load_model():

    global _model

    if _model is not None:
        return _model

    if not CHECKPOINT.exists():
        raise FileNotFoundError(
            "Model checkpoint not found:\n"
            f"{CHECKPOINT}"
        )

    print(
        "\nLoading Depth Anything V2 model..."
    )

    model = DepthAnythingV2(
        **MODEL_CONFIG[ENCODER]
    )

    checkpoint = torch.load(
        CHECKPOINT,
        map_location=DEVICE,
        weights_only=False,
    )

    if isinstance(
        checkpoint,
        dict,
    ):

        if (
            "model_state_dict"
            in checkpoint
        ):
            state_dict = (
                checkpoint[
                    "model_state_dict"
                ]
            )

        elif (
            "state_dict"
            in checkpoint
        ):
            state_dict = (
                checkpoint[
                    "state_dict"
                ]
            )

        else:
            state_dict = checkpoint

    else:
        state_dict = checkpoint

    model.load_state_dict(
        state_dict,
        strict=True,
    )

    model = model.to(
        DEVICE
    )

    model.eval()

    _model = model

    print(
        "Model loaded successfully."
    )

    return _model


# ============================================================
# LOAD GLOBAL CALIBRATION
# ============================================================

def load_global_calibration():

    global _linear_slope
    global _linear_intercept

    if (
        _linear_slope is not None
        and _linear_intercept is not None
    ):
        return (
            _linear_slope,
            _linear_intercept,
        )

    if not CALIBRATION_FILE.exists():

        print(
            "\nGlobal calibration file not found."
        )

        _linear_slope = None
        _linear_intercept = None

        return (
            None,
            None,
        )

    try:

        calibration = np.load(
            CALIBRATION_FILE
        )

        if (
            "linear_slope"
            not in calibration
        ):
            raise KeyError(
                "linear_slope missing."
            )

        if (
            "linear_intercept"
            not in calibration
        ):
            raise KeyError(
                "linear_intercept missing."
            )

        _linear_slope = float(
            calibration[
                "linear_slope"
            ]
        )

        _linear_intercept = float(
            calibration[
                "linear_intercept"
            ]
        )

        print(
            "\nGlobal calibration loaded."
        )

        print(
            f"Slope     : "
            f"{_linear_slope:.8f}"
        )

        print(
            f"Intercept : "
            f"{_linear_intercept:.8f}"
        )

        return (
            _linear_slope,
            _linear_intercept,
        )

    except Exception as exc:

        print(
            "\nCould not load global calibration:"
        )

        print(
            exc
        )

        _linear_slope = None
        _linear_intercept = None

        return (
            None,
            None,
        )


# ============================================================
# LOAD RGB IMAGE
# ============================================================

def load_rgb_image(
    image_path,
):

    image_path = Path(
        image_path
    )

    if not image_path.exists():
        raise FileNotFoundError(
            f"Input image not found:\n"
            f"{image_path}"
        )

    try:

        image = Image.open(
            image_path
        ).convert("RGB")

    except Exception as exc:

        raise ValueError(
            f"Could not open image: {exc}"
        )

    return np.asarray(
        image,
        dtype=np.uint8,
    )


# ============================================================
# PREPROCESS IMAGE
# ============================================================

def preprocess_rgb(
    rgb,
):

    original_height = (
        rgb.shape[0]
    )

    original_width = (
        rgb.shape[1]
    )

    # Copy so torch does not receive a
    # read-only NumPy buffer.
    image = np.array(
        rgb,
        dtype=np.uint8,
        copy=True,
    )

    image = (
        torch.from_numpy(
            image
        )
        .float()
        / 255.0
    )

    image = image.permute(
        2,
        0,
        1,
    )

    image = image.unsqueeze(0)

    image = F.interpolate(
        image,
        size=(
            INPUT_SIZE,
            INPUT_SIZE,
        ),
        mode="bilinear",
        align_corners=False,
    )

    mean = torch.tensor(
        [
            0.485,
            0.456,
            0.406,
        ],
        dtype=torch.float32,
        device=DEVICE,
    ).view(
        1,
        3,
        1,
        1,
    )

    std = torch.tensor(
        [
            0.229,
            0.224,
            0.225,
        ],
        dtype=torch.float32,
        device=DEVICE,
    ).view(
        1,
        3,
        1,
        1,
    )

    image = image.to(
        DEVICE
    )

    image = (
        image - mean
    ) / std

    return (
        image,
        original_height,
        original_width,
    )


# ============================================================
# RUN DEPTH INFERENCE
# ============================================================

@torch.inference_mode()
def predict_relative_depth(
    rgb,
):

    model = load_model()

    (
        image,
        original_height,
        original_width,
    ) = preprocess_rgb(
        rgb
    )

    print(
        "\nRunning depth inference..."
    )

    prediction = model(
        image
    )

    if prediction.ndim == 3:

        prediction = (
            prediction.unsqueeze(1)
        )

    prediction = F.interpolate(
        prediction,
        size=(
            original_height,
            original_width,
        ),
        mode="bilinear",
        align_corners=False,
    )

    prediction = prediction[
        0,
        0,
    ]

    prediction = (
        prediction
        .detach()
        .cpu()
        .numpy()
        .astype(
            np.float32
        )
    )

    if not np.isfinite(
        prediction
    ).any():

        raise ValueError(
            "Depth model produced no finite values."
        )

    print(
        f"Raw prediction range: "
        f"{np.nanmin(prediction):.6f}"
        f" → "
        f"{np.nanmax(prediction):.6f}"
    )

    return prediction


# ============================================================
# CLEAN DEPTH
# ============================================================

def clean_depth(
    prediction,
):

    prediction = np.asarray(
        prediction,
        dtype=np.float32,
    ).copy()

    finite_mask = np.isfinite(
        prediction
    )

    if not finite_mask.any():

        raise ValueError(
            "Depth prediction contains no finite values."
        )

    median_value = float(
        np.median(
            prediction[
                finite_mask
            ]
        )
    )

    prediction[
        ~finite_mask
    ] = median_value

    return prediction


# ============================================================
# DEPTH DENOISING
# ============================================================

def refine_raw_depth(
    raw_prediction,
):
    """
    Mild two-stage refinement:

    1. Median filter:
       removes isolated spikes.

    2. Bilateral filter:
       reduces local noise while preserving
       larger structural transitions.
    """

    depth = clean_depth(
        raw_prediction
    )

    print(
        "\nRefining raw depth..."
    )

    print(
        f"Median kernel:"
        f" {MEDIAN_KERNEL}"
    )

    print(
        f"Bilateral diameter:"
        f" {BILATERAL_DIAMETER}"
    )

    median_depth = cv2.medianBlur(
        depth,
        MEDIAN_KERNEL,
    )

    bilateral_depth = cv2.bilateralFilter(
        median_depth,
        BILATERAL_DIAMETER,
        BILATERAL_SIGMA_COLOR,
        BILATERAL_SIGMA_SPACE,
    )

    bilateral_depth = np.nan_to_num(
        bilateral_depth,
        nan=float(
            np.median(
                bilateral_depth
            )
        ),
        posinf=float(
            np.max(
                bilateral_depth[
                    np.isfinite(
                        bilateral_depth
                    )
                ]
            )
        ),
        neginf=float(
            np.min(
                bilateral_depth[
                    np.isfinite(
                        bilateral_depth
                    )
                ]
            )
        ),
    )

    print(
        "\nRefined depth range:"
    )

    print(
        f"{bilateral_depth.min():.6f}"
        f" → "
        f"{bilateral_depth.max():.6f}"
    )

    return bilateral_depth.astype(
        np.float32
    )


# ============================================================
# CREATE RELATIVE rDSM
# ============================================================

def create_relative_rdsm(
    refined_depth,
):
    """
    Convert the refined relative depth prediction
    into a stable 0..1 relative surface.

    This is the PRIMARY output for the
    non-georeferenced pipeline.
    """

    depth = clean_depth(
        refined_depth
    )

    low_value = float(
        np.percentile(
            depth,
            LOW_PERCENTILE,
        )
    )

    high_value = float(
        np.percentile(
            depth,
            HIGH_PERCENTILE,
        )
    )

    print(
        "\nRobust normalization:"
    )

    print(
        f"P{LOW_PERCENTILE:g}: "
        f"{low_value:.6f}"
    )

    print(
        f"P{HIGH_PERCENTILE:g}: "
        f"{high_value:.6f}"
    )

    if high_value <= low_value:

        raise ValueError(
            "Invalid percentile range."
        )

    relative = (
        depth
        - low_value
    ) / (
        high_value
        - low_value
    )

    relative = np.clip(
        relative,
        0.0,
        1.0,
    )

    relative = relative.astype(
        np.float32
    )

    print(
        "\nRelative rDSM range:"
    )

    print(
        f"{relative.min():.6f}"
        f" → "
        f"{relative.max():.6f}"
    )

    return (
        relative,
        low_value,
        high_value,
    )


# ============================================================
# GLOBAL METRIC BASELINE
# ============================================================

def create_metric_baseline(
    raw_prediction,
):
    """
    Optional GAMUS global metric baseline.

    IMPORTANT:
    Calibration is applied to the RAW model
    prediction, not the 0..1 normalized rDSM.

    This baseline is NOT used as the primary
    non-georeferenced mesh.
    """

    if not USE_GLOBAL_CALIBRATION:

        return None

    (
        slope,
        intercept,
    ) = load_global_calibration()

    if (
        slope is None
        or intercept is None
    ):

        return None

    raw = clean_depth(
        raw_prediction
    )

    metric = (
        slope
        * raw
        + intercept
    )

    if CLIP_METRIC_TO_ZERO:

        metric = np.maximum(
            metric,
            0.0,
        )

    metric = np.nan_to_num(
        metric,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    metric = metric.astype(
        np.float32
    )

    print(
        "\nMetric baseline range:"
    )

    print(
        f"{metric.min():.6f}"
        f" → "
        f"{metric.max():.6f} m"
    )

    return metric


# ============================================================
# SAVE NUMPY
# ============================================================

def save_numpy(
    array,
    path,
):

    np.save(
        path,
        array.astype(
            np.float32
        ),
    )

    print(
        f"Saved NPY:\n{path}"
    )


# ============================================================
# SAVE VISUALIZATION
# ============================================================

def save_visualization(
    array,
    path,
):

    array = np.asarray(
        array,
        dtype=np.float32,
    )

    minimum = float(
        np.min(array)
    )

    maximum = float(
        np.max(array)
    )

    if maximum > minimum:

        normalized = (
            array - minimum
        ) / (
            maximum - minimum
        )

    else:

        normalized = np.zeros_like(
            array
        )

    image = (
        normalized
        * 255.0
    ).clip(
        0,
        255,
    ).astype(
        np.uint8
    )

    Image.fromarray(
        image,
        mode="L",
    ).save(
        path
    )

    print(
        f"Saved preview:\n{path}"
    )


# ============================================================
# PROCESS IMAGE
# ============================================================

def process_image(
    image_path,
    scene_name=None,
):

    image_path = Path(
        image_path
    )

    if scene_name is None:

        scene_name = (
            image_path.stem
        )

    print(
        "\n" + "=" * 75
    )

    print(
        "GEOSCULPT - IMAGE PROCESSING"
    )

    print(
        "=" * 75
    )

    print(
        f"\nInput image:"
        f"\n{image_path}"
    )

    print(
        f"\nScene:"
        f"\n{scene_name}"
    )

    # --------------------------------------------------------
    # Load RGB image
    # --------------------------------------------------------

    rgb = load_rgb_image(
        image_path
    )

    height, width = (
        rgb.shape[:2]
    )

    print(
        f"\nImage size: "
        f"{width} × {height}"
    )

    # --------------------------------------------------------
    # Raw model depth
    # --------------------------------------------------------

    raw_prediction = (
        predict_relative_depth(
            rgb
        )
    )

    # --------------------------------------------------------
    # Refine raw depth
    # --------------------------------------------------------

    refined_depth = (
        refine_raw_depth(
            raw_prediction
        )
    )

    # --------------------------------------------------------
    # Relative rDSM
    # --------------------------------------------------------

    (
        relative_rdsm,
        low_value,
        high_value,
    ) = create_relative_rdsm(
        refined_depth
    )

    # --------------------------------------------------------
    # Metric baseline
    #
    # Applied to RAW prediction only.
    # --------------------------------------------------------

    metric_baseline = (
        create_metric_baseline(
            raw_prediction
        )
    )

    # --------------------------------------------------------
    # Output paths
    # --------------------------------------------------------

    raw_npy = (
        OUTPUT_DIR
        / f"{scene_name}_raw_depth.npy"
    )

    refined_npy = (
        OUTPUT_DIR
        / f"{scene_name}_refined_depth.npy"
    )

    relative_npy = (
        OUTPUT_DIR
        / f"{scene_name}_relative.npy"
    )

    relative_png = (
        OUTPUT_DIR
        / f"{scene_name}_relative.png"
    )

    metric_npy = (
        OUTPUT_DIR
        / f"{scene_name}_metric_rDSM.npy"
    )

    metric_png = (
        OUTPUT_DIR
        / f"{scene_name}_metric_rDSM.png"
    )

    # --------------------------------------------------------
    # Save raw depth
    # --------------------------------------------------------

    save_numpy(
        raw_prediction,
        raw_npy,
    )

    # --------------------------------------------------------
    # Save refined depth
    # --------------------------------------------------------

    save_numpy(
        refined_depth,
        refined_npy,
    )

    # --------------------------------------------------------
    # Save relative rDSM
    # --------------------------------------------------------

    save_numpy(
        relative_rdsm,
        relative_npy,
    )

    save_visualization(
        relative_rdsm,
        relative_png,
    )

    # --------------------------------------------------------
    # Save optional metric baseline
    # --------------------------------------------------------

    if metric_baseline is not None:

        save_numpy(
            metric_baseline,
            metric_npy,
        )

        save_visualization(
            metric_baseline,
            metric_png,
        )

    else:

        metric_npy = None
        metric_png = None

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print(
        "\n" + "=" * 75
    )

    print(
        "DEPTH / rDSM PROCESSING COMPLETE"
    )

    print(
        "=" * 75
    )

    print(
        "\nPrimary non-georeferenced output:"
    )

    print(
        "Relative rDSM"
    )

    print(
        f"\nRelative NPY:"
        f"\n{relative_npy}"
    )

    print(
        f"\nRelative preview:"
        f"\n{relative_png}"
    )

    print(
        f"\nRefined depth:"
        f"\n{refined_npy}"
    )

    if metric_baseline is not None:

        print(
            "\nOptional metric baseline:"
        )

        print(
            f"\n{metric_npy}"
        )

    return {
        "raw_prediction":
            raw_prediction,

        "refined_depth":
            refined_depth,

        "relative_depth":
            relative_rdsm,

        "metric_rdsm":
            metric_baseline,

        "raw_npy":
            raw_npy,

        "refined_npy":
            refined_npy,

        "relative_npy":
            relative_npy,

        "relative_png":
            relative_png,

        "metric_npy":
            metric_npy,

        "metric_png":
            metric_png,

        "shape": [
            int(height),
            int(width),
        ],

        "normalization": {
            "low_percentile":
                LOW_PERCENTILE,

            "high_percentile":
                HIGH_PERCENTILE,

            "low_value":
                low_value,

            "high_value":
                high_value,
        },

        "metric_calibration_used":
            metric_baseline is not None,
    }


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":

    test_image = (
        ROOT
        / "uploads"
        / "test.jpg"
    )

    if not test_image.exists():

        print(
            "\nTest image not found:"
        )

        print(
            test_image
        )

    else:

        result = process_image(
            test_image,
            scene_name="test",
        )

        print(
            "\nTEST SUCCESS"
        )

        print(
            f"Shape:"
            f" {result['shape']}"
        )