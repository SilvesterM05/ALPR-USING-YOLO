import os
import cv2
import pandas as pd
from ultralytics import YOLO

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

PLATE_FOLDER = os.path.join(
    BASE_PATH,
    "plates"
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

os.makedirs(PLATE_FOLDER, exist_ok=True)

os.makedirs(CSV_FOLDER, exist_ok=True)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# =========================================================
# TARGET CHARACTERS
# =========================================================

TARGET_CHARS = list(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
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

# =========================================================
# MODEL PATHS
# =========================================================

PLATE_MODEL_PATH = (
    "plate_best/wiitronics-lpvd-plate.pt"
)

CHAR_MODEL_PATH = (
    "lpcd-character/weights/best.pt"
)

# =========================================================
# LOAD MODELS
# =========================================================

print("\nLoading models...")

plate_model = YOLO(PLATE_MODEL_PATH)

char_model = YOLO(CHAR_MODEL_PATH)

print("Models loaded.")

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

print(f"\nFound {len(image_files)} images")

# =========================================================
# PROCESS IMAGES
# =========================================================

for img_file in image_files:

    print("\n================================================")
    print(f"PROCESSING: {img_file}")
    print("================================================")

    plate_text = os.path.splitext(
        img_file
    )[0].upper()

    img_path = os.path.join(
        INPUT_FOLDER,
        img_file
    )

    # =====================================================
    # READ IMAGE
    # =====================================================

    img = cv2.imread(img_path)

    if img is None:

        print("Could not read image")

        continue

    # =====================================================
    # PLATE DETECTION
    # =====================================================

    plate_results = plate_model.predict(
        source=img,
        conf=0.20,
        verbose=False
    )

    plate_boxes = plate_results[0].boxes

    print(
        f"Plate detections: "
        f"{len(plate_boxes)}"
    )

    if len(plate_boxes) == 0:

        print("No plate detected")

        continue

    # =====================================================
    # TAKE FIRST PLATE
    # =====================================================

    plate_box = plate_boxes.xyxy[0]

    px1, py1, px2, py2 = map(
        int,
        plate_box.cpu().numpy()
    )

    # =====================================================
    # CROP PLATE
    # =====================================================

    plate_crop = img[
        py1:py2,
        px1:px2
    ]

    if plate_crop.size == 0:

        print("Invalid plate crop")

        continue

    # =====================================================
    # SAVE DETECTED PLATE
    # =====================================================

    plate_save_path = os.path.join(
        PLATE_FOLDER,
        f"{plate_text}.jpg"
    )

    cv2.imwrite(
        plate_save_path,
        plate_crop
    )

    print(
        f"Saved plate: "
        f"{plate_save_path}"
    )

    # =====================================================
    # ENLARGE FOR CHARACTER DETECTION
    # =====================================================

    enlarged_plate = cv2.resize(
        plate_crop,
        None,
        fx=3,
        fy=3,
        interpolation=cv2.INTER_CUBIC
    )

    # =====================================================
    # CHARACTER DETECTION
    # =====================================================

    char_results = char_model.predict(
        source=enlarged_plate,
        conf=0.05,
        verbose=False
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
    # STORE BOXES
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

        cx1 = int(cx1 / 3)
        cy1 = int(cy1 / 3)

        cx2 = int(cx2 / 3)
        cy2 = int(cy2 / 3)

        detections.append({
            "x1": cx1,
            "y1": cy1,
            "x2": cx2,
            "y2": cy2
        })

    # =====================================================
    # SORT LEFT → RIGHT
    # =====================================================

    detections = sorted(
        detections,
        key=lambda d: d["x1"]
    )

    print(
        f"Usable detections: "
        f"{len(detections)}"
    )

    # =====================================================
    # MATCH DETECTIONS WITH FILENAME
    # =====================================================

    usable_count = min(
        len(detections),
        len(plate_text)
    )

    print(
        f"Filename chars: "
        f"{len(plate_text)}"
    )

    print(
        f"Using: "
        f"{usable_count}"
    )

    # =====================================================
    # CREATE CSV DATA
    # =====================================================

    csv_rows = []

    # =====================================================
    # PROCESS EACH DETECTION
    # =====================================================

    for idx in range(usable_count):

        det = detections[idx]

        actual_char = plate_text[idx]

        # skip unsupported chars
        if actual_char not in TARGET_CHARS:
            continue

        x1 = det["x1"]
        y1 = det["y1"]
        x2 = det["x2"]
        y2 = det["y2"]

        # =================================================
        # BOX SIZE
        # =================================================

        box_w = x2 - x1
        box_h = y2 - y1

        if (
            box_w < MIN_BOX_SIZE or
            box_h < MIN_BOX_SIZE
        ):
            continue

        # =================================================
        # PADDING
        # =================================================

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
        # CROP USING DETECTION BOX
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

        print(
            f"Saved: {save_path}"
        )

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

        print(
            f"CSV Saved: "
            f"{csv_save_path}"
        )

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