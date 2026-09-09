from pathlib import Path

import cv2
import numpy as np
from PIL import Image


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent

DEPTH_DIR = (
    ROOT
    / "results"
    / "depth"
)

DIAGNOSTIC_DIR = (
    DEPTH_DIR
    / "diagnostics"
)

DIAGNOSTIC_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# FIND LATEST RAW DEPTH
# ============================================================

raw_files = sorted(
    DEPTH_DIR.glob(
        "*_raw_depth.npy"
    ),
    key=lambda p: p.stat().st_mtime,
)

if not raw_files:
    raise FileNotFoundError(
        "No raw depth NPY files found in:\n"
        f"{DEPTH_DIR}"
    )

raw_file = raw_files[-1]


# ============================================================
# LOAD RAW DEPTH
# ============================================================

depth = np.load(
    raw_file
).astype(
    np.float32
)


# ============================================================
# VALIDATION
# ============================================================

if depth.ndim != 2:
    raise ValueError(
        f"Expected a 2D depth map, got {depth.shape}"
    )

finite_mask = np.isfinite(
    depth
)

if not finite_mask.any():
    raise ValueError(
        "Depth map contains no finite values."
    )


valid = depth[
    finite_mask
]


# ============================================================
# BASIC STATISTICS
# ============================================================

print()
print("=" * 75)
print("GEOSCULPT - RAW DEPTH DIAGNOSTIC")
print("=" * 75)

print(
    f"\nFile:"
    f"\n{raw_file}"
)

print(
    f"\nShape:"
    f" {depth.shape[0]} × {depth.shape[1]}"
)

print(
    f"\nFinite pixels:"
    f" {finite_mask.sum():,}"
)

print(
    f"\nMinimum:"
    f" {valid.min():.6f}"
)

print(
    f"Maximum:"
    f" {valid.max():.6f}"
)

print(
    f"Mean:"
    f" {valid.mean():.6f}"
)

print(
    f"Median:"
    f" {np.median(valid):.6f}"
)

print(
    f"Std:"
    f" {valid.std():.6f}"
)


# ============================================================
# PERCENTILES
# ============================================================

percentiles = [
    1,
    2,
    5,
    10,
    25,
    50,
    75,
    90,
    95,
    98,
    99,
]

print(
    "\nPercentiles:"
)

print(
    "-" * 50
)

for p in percentiles:

    value = np.percentile(
        valid,
        p,
    )

    print(
        f"P{p:>2}:"
        f" {value:.6f}"
    )


# ============================================================
# EDGE STATISTICS
# ============================================================

height, width = depth.shape

edge = max(
    1,
    int(
        min(
            height,
            width,
        )
        * 0.05
    ),
)

top = depth[
    :edge,
    :
]

bottom = depth[
    -edge:,
    :
]

left = depth[
    :,
    :edge
]

right = depth[
    :,
    -edge:
]

print(
    "\nEdge statistics:"
)

print(
    "-" * 50
)

print(
    f"Top mean    : "
    f"{np.mean(top):.6f}"
)

print(
    f"Bottom mean : "
    f"{np.mean(bottom):.6f}"
)

print(
    f"Left mean   : "
    f"{np.mean(left):.6f}"
)

print(
    f"Right mean  : "
    f"{np.mean(right):.6f}"
)


# ============================================================
# CENTER STATISTICS
# ============================================================

y1 = int(
    height * 0.25
)

y2 = int(
    height * 0.75
)

x1 = int(
    width * 0.25
)

x2 = int(
    width * 0.75
)

center = depth[
    y1:y2,
    x1:x2
]

print(
    "\nCenter statistics:"
)

print(
    "-" * 50
)

print(
    f"Center mean:"
    f" {np.mean(center):.6f}"
)

print(
    f"Center median:"
    f" {np.median(center):.6f}"
)

print(
    f"Center std:"
    f" {np.std(center):.6f}"
)


# ============================================================
# FOUR-QUADRANT STATISTICS
# ============================================================

half_h = height // 2
half_w = width // 2

quadrants = {
    "Top-left":
        depth[
            :half_h,
            :half_w
        ],

    "Top-right":
        depth[
            :half_h,
            half_w:
        ],

    "Bottom-left":
        depth[
            half_h:,
            :half_w
        ],

    "Bottom-right":
        depth[
            half_h:,
            half_w:
        ],
}

print(
    "\nQuadrant means:"
)

print(
    "-" * 50
)

for name, region in quadrants.items():

    print(
        f"{name:<15}: "
        f"{np.mean(region):.6f}"
    )


# ============================================================
# ROW PROFILE
# ============================================================

row_means = np.mean(
    depth,
    axis=1,
)

col_means = np.mean(
    depth,
    axis=0,
)

print(
    "\nLarge-scale spatial variation:"
)

print(
    "-" * 50
)

print(
    f"Row mean min:"
    f" {row_means.min():.6f}"
)

print(
    f"Row mean max:"
    f" {row_means.max():.6f}"
)

print(
    f"Column mean min:"
    f" {col_means.min():.6f}"
)

print(
    f"Column mean max:"
    f" {col_means.max():.6f}"
)


# ============================================================
# SMOOTH LARGE-SCALE SURFACE
# ============================================================

smooth = cv2.GaussianBlur(
    depth,
    (
        51,
        51,
    ),
    0,
)


residual = (
    depth - smooth
)


# ============================================================
# RESIDUAL STATISTICS
# ============================================================

residual_valid = residual[
    finite_mask
]

print(
    "\nHigh-frequency residual:"
)

print(
    "-" * 50
)

print(
    f"Residual min:"
    f" {residual_valid.min():.6f}"
)

print(
    f"Residual max:"
    f" {residual_valid.max():.6f}"
)

print(
    f"Residual mean:"
    f" {residual_valid.mean():.6f}"
)

print(
    f"Residual std:"
    f" {residual_valid.std():.6f}"
)


# ============================================================
# SAVE NORMALIZED RAW DEPTH
# ============================================================

low = np.percentile(
    valid,
    2,
)

high = np.percentile(
    valid,
    98,
)

normalized = (
    depth - low
) / (
    high - low
)

normalized = np.clip(
    normalized,
    0,
    1,
)

raw_vis = (
    normalized
    * 255
).astype(
    np.uint8
)

raw_vis_path = (
    DIAGNOSTIC_DIR
    / f"{raw_file.stem}_visualization.png"
)

Image.fromarray(
    raw_vis,
    mode="L",
).save(
    raw_vis_path
)


# ============================================================
# SAVE SMOOTH SURFACE
# ============================================================

smooth_low = np.percentile(
    smooth,
    2,
)

smooth_high = np.percentile(
    smooth,
    98,
)

smooth_vis = (
    smooth - smooth_low
) / (
    smooth_high
    - smooth_low
)

smooth_vis = np.clip(
    smooth_vis,
    0,
    1,
)

smooth_vis = (
    smooth_vis
    * 255
).astype(
    np.uint8
)

smooth_path = (
    DIAGNOSTIC_DIR
    / f"{raw_file.stem}_smooth.png"
)

Image.fromarray(
    smooth_vis,
    mode="L",
).save(
    smooth_path
)


# ============================================================
# SAVE RESIDUAL
# ============================================================

res_low = np.percentile(
    residual,
    2,
)

res_high = np.percentile(
    residual,
    98,
)

residual_vis = (
    residual - res_low
) / (
    res_high - res_low
)

residual_vis = np.clip(
    residual_vis,
    0,
    1,
)

residual_vis = (
    residual_vis
    * 255
).astype(
    np.uint8
)

residual_path = (
    DIAGNOSTIC_DIR
    / f"{raw_file.stem}_residual.png"
)

Image.fromarray(
    residual_vis,
    mode="L",
).save(
    residual_path
)


# ============================================================
# SAVE CENTER PROFILE
# ============================================================

center_row = depth[
    height // 2,
    :
]

center_col = depth[
    :,
    width // 2
]

np.save(
    DIAGNOSTIC_DIR
    / f"{raw_file.stem}_row_profile.npy",
    center_row,
)

np.save(
    DIAGNOSTIC_DIR
    / f"{raw_file.stem}_column_profile.npy",
    center_col,
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print(
    "\nDiagnostic images saved:"
)

print(
    f"\nRaw:"
    f"\n{raw_vis_path}"
)

print(
    f"\nSmooth:"
    f"\n{smooth_path}"
)

print(
    f"\nResidual:"
    f"\n{residual_path}"
)

print(
    "\n" + "=" * 75
)

print(
    "DEPTH DIAGNOSTIC COMPLETE"
)

print(
    "=" * 75
)