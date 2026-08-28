# Automatic License Plate Recognition (ALPR) Pipeline

An end-to-end computer vision pipeline for vehicle license plate localization, character segmentation, and alphanumeric classification using YOLO and EfficientNet-B0.

---

## 📌 Architecture Overview

The system processes input images through a three-stage pipeline:
1. **Stage 1 — Plate Localization:** Custom-trained YOLO model locates the license plate boundary within raw camera feeds.
2. **Stage 2 — Character Segmentation:** YOLO-based character detector extracts individual bounding boxes for each character.
3. **Stage 3 — Character Classification:** EfficientNet-B0 CNN classifies cropped character regions across 36 alphanumeric classes (0–9, A–Z).

```text
Input Image ──► YOLO (Plate Detect) ──► Crop & Filter ──► YOLO (Char Detect) ──► EfficientNet-B0 ──► Plate String
📁 Repository Structure
final.py — Main inference script executing the multi-stage ALPR pipeline.

seperation.py — Preprocessing module for sorting, cropping, and directory-based structuring of detected character regions.

marinaimg.py — Image enhancement utilities (Otsu thresholding, contrast adjustment, and noise reduction).

download.py — Parallelized image ingestion script with rate limiting and automated retry logic.

🛠️ Tech Stack
Language: Python 3.10+

Computer Vision & Deep Learning: OpenCV, PyTorch, Ultralytics YOLO, EfficientNet-B0, Scikit-learn

Data Handling: NumPy, Pandas


3. Click the green **Commit changes...** button at the top right, then click **Commit changes** again on the pop-up.

### Step 2: Add the Requirements File
1. On your main repository page, click the **Add file** button (near the top right, next to the green Code button) and select **Create new file**.
2. Name the file exactly `requirements.txt`.
3. Paste these dependencies into the blank space:

```text
opencv-python
torch
torchvision
ultralytics
scikit-learn
numpy
pandas
