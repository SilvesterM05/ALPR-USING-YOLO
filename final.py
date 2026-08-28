import os
import cv2
import torch
import pandas as pd
from ultralytics import YOLO

# =========================================================
# GPU CHECK
# =========================================================

if torch.cuda.is_available():

    DEVICE = "cuda"

    print("\n===================================")
    print("GPU DETECTED")
    print(f"GPU Name: {torch.cuda.get_device_name(0)}")
    print("Running on CUDA")
    print("===================================\n")

else:

    DEVICE = "cpu"

    print("\n===================================")
    print("NO GPU DETECTED")
    print("Running on CPU")
    print("===================================\n")

# =========================================================
# BASE PATH
# =========================================================

BASE_PATH = r"C:\Users\msilv\Desktop\Wiitronics clg\plate_character_seperation"

# =========================================================
# INPUT / OUTPUT FOLDERS
# =========================================================

INPUT_FOLDER = os.path.join(
    BASE_PATH,
    "input_fol"
)

CSV_FOLDER = os.path.join(
    BASE_PATH,
    "csv"
)

OUTPUT_FOLDER = os.path.join(
    BASE_PATH,
    "characters"
)

# =========================================================
# CREATE FOLDERS
# =========================================================

os.makedirs(CSV_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# =========================================================
# TARGET CHARACTERS
# =========================================================

TARGET_CHARS = list(
    "GIOPRUVWXYZ"
)

# create class folders
for ch in TARGET_CHARS:

    os.makedirs(
        os.path.join(OUTPUT_FOLDER, ch),
        exist_ok=True
    )

# =========================================================
# SETTINGS
# =========================================================

OUTPUT_SIZE = 128

PADDING = 0.20

MIN_BOX_SIZE = 5

UPSCALE_FACTOR = 3

# =========================================================
# MODEL PATH
# =========================================================

CHAR_MODEL_PATH = (
    "lpcd-character/weights/best.pt"
)

# =========================================================
# LOAD MODEL TO GPU
# =========================================================

print("Loading YOLO model...")

char_model = YOLO(CHAR_MODEL_PATH)

# move model to gpu
char_model.to(DEVICE)

print("Model loaded.")

# =========================================================
# STATS
# =========================================================

saved_count = 0

# =========================================================
# IMAGE FILES
# =========================================================

image_files = [
    f for f in os.listdir(INPUT_FOLDER)
    if f.lower().endswith(
        (".jpg", ".jpeg", ".png")
    )
]

print(f"\nFound {len(image_files)} plate images")

# =========================================================
# PROCESS IMAGES
# =========================================================

for img_file in image_files:

    print("\n================================================")
    print(f"PROCESSING: {img_file}")
    print("================================================")

    # =====================================================
    # LABEL FROM FILENAME
    # =====================================================

    plate_text = os.path.splitext(
        img_file
    )[0].upper()

    plate_text = "".join(
        ch for ch in plate_text
        if ch.isalnum()
    )

    img_path = os.path.join(
        INPUT_FOLDER,
        img_file
    )

    # =====================================================
    # READ IMAGE
    # =====================================================

    plate_crop = cv2.imread(img_path)

    if plate_crop is None:

        print("Could not read image")

        continue

    # =====================================================
    # UPSCALE IMAGE
    # =====================================================

    enlarged_plate = cv2.resize(
        plate_crop,
        None,
        fx=UPSCALE_FACTOR,
        fy=UPSCALE_FACTOR,
        interpolation=cv2.INTER_CUBIC
    )

    # =====================================================
    # CHARACTER DETECTION (GPU)
    # =====================================================

    char_results = char_model.predict(
        source=enlarged_plate,
        conf=0.05,
        verbose=False,
        device=DEVICE
    )

    char_boxes = char_results[0].boxes

    print(
        f"Character detections: "
        f"{len(char_boxes)}"
    )

    if len(char_boxes) == 0:

        print("No characters detected")

        continue

    # =====================================================
    # STORE DETECTIONS
    # =====================================================

    detections = []

    for box in char_boxes:

        cls_id = int(box.cls[0])

        class_name = str(
            char_model.names[cls_id]
        ).upper()

        # skip IND logo
        if class_name == "IND":
            continue

        cx1, cy1, cx2, cy2 = map(
            int,
            box.xyxy[0].cpu().numpy()
        )

        # =================================================
        # SCALE BACK
        # =================================================

        cx1 = int(cx1 / UPSCALE_FACTOR)
        cy1 = int(cy1 / UPSCALE_FACTOR)

        cx2 = int(cx2 / UPSCALE_FACTOR)
        cy2 = int(cy2 / UPSCALE_FACTOR)

        box_w = cx2 - cx1
        box_h = cy2 - cy1

        if (
            box_w < MIN_BOX_SIZE or
            box_h < MIN_BOX_SIZE
        ):
            continue

        detections.append({
            "x1": cx1,
            "y1": cy1,
            "x2": cx2,
            "y2": cy2
        })

    # =====================================================
    # SORT LEFT TO RIGHT
    # =====================================================

    detections = sorted(
        detections,
        key=lambda d: d["x1"]
    )

    print(
        f"Usable detections: "
        f"{len(detections)}"
    )

    usable_count = min(
        len(detections),
        len(plate_text)
    )

    # =====================================================
    # CSV STORAGE
    # =====================================================

    csv_rows = []

    # =====================================================
    # PROCESS EACH CHARACTER
    # =====================================================

    for idx in range(usable_count):

        det = detections[idx]

        actual_char = plate_text[idx]

        if actual_char not in TARGET_CHARS:
            continue

        x1 = det["x1"]
        y1 = det["y1"]
        x2 = det["x2"]
        y2 = det["y2"]

        # =================================================
        # PADDING
        # =================================================

        box_w = x2 - x1
        box_h = y2 - y1

        pad_w = int(box_w * PADDING)
        pad_h = int(box_h * PADDING)

        x1_p = max(0, x1 - pad_w)
        y1_p = max(0, y1 - pad_h)

        x2_p = min(
            plate_crop.shape[1],
            x2 + pad_w
        )

        y2_p = min(
            plate_crop.shape[0],
            y2 + pad_h
        )

        # =================================================
        # CHARACTER CROP
        # =================================================

        crop = plate_crop[
            y1_p:y2_p,
            x1_p:x2_p
        ]

        if crop.size == 0:
            continue

        # =================================================
        # RESIZE
        # =================================================

        crop = cv2.resize(
            crop,
            (OUTPUT_SIZE, OUTPUT_SIZE)
        )

        # =================================================
        # SAVE
        # =================================================

        save_name = (
            f"{plate_text}_{idx}.jpg"
        )

        save_path = os.path.join(
            OUTPUT_FOLDER,
            actual_char,
            save_name
        )

        cv2.imwrite(
            save_path,
            crop
        )

        saved_count += 1

        print(f"Saved: {save_path}")

        # =================================================
        # CSV ROW
        # =================================================

        csv_rows.append({
            "character": actual_char,
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2
        })

    # =====================================================
    # SAVE CSV
    # =====================================================

    if len(csv_rows) > 0:

        df = pd.DataFrame(csv_rows)

        csv_save_path = os.path.join(
            CSV_FOLDER,
            f"{plate_text}.csv"
        )

        df.to_csv(
            csv_save_path,
            index=False
        )

        print(f"CSV Saved: {csv_save_path}")

# =========================================================
# DONE
# =========================================================

print("\n================================================")
print("DONE")
print("================================================")

print(
    f"Total characters saved: "
    f"{saved_count}"
)