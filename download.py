import requests
import base64
import os
import time
import json
import certifi
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# =========================================================
# SAFE SSL
# =========================================================

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================================================
# CONFIG
# =========================================================

START_DATE = "2026-02-01"
END_DATE   = "2026-02-01"

# =========================================================
# VEHICLE FILTERS
# =========================================================
# It will create separate folders for each filter
#
# Example:
# "A" -> all vehicles containing A
# "TN" -> all TN vehicles
# "Z" -> all containing Z
#
# ADD OR REMOVE ANYTHING HERE
# =========================================================

VEHICLE_FILTERS = [
    "N"
]

# =========================================================
# API URLS
# =========================================================

POS_GET_URL = "https://mdu-tmlcp.parklensindia.com/ops/pos_get"

DOWNLOAD_URL = "https://mdu-tmlcp.parklensindia.com/ops/download_image"

# =========================================================
# HEADERS
# =========================================================

HEADERS = {
    "accept": "*/*",
    "content-type": "application/json",
    "origin": "https://mdu-tmlcp.parklensindia.com",
    "referer": "https://mdu-tmlcp.parklensindia.com/new-portal/auth/detailed_transaction",
    "user-agent": "Mozilla/5.0",

    "AccessToken": "595248474b444f49436265613839724d5a7139546e304e74575538427170796171433278303756351",

    "AuthCode": "744e674466615267786e356658736538"
}

# =========================================================
# SAVE ROOT
# =========================================================

ROOT_FOLDER = f"vehicle_downloads_{START_DATE}_to_{END_DATE}"

os.makedirs(ROOT_FOLDER, exist_ok=True)

# =========================================================
# REQUEST SESSION
# =========================================================

session = requests.Session()
session.verify = certifi.where()

# =========================================================
# THREAD SETTINGS
# =========================================================
# KEEP THIS SAFE
#
# 3-5 = Safe
# 10+ = risky for API
# =========================================================

MAX_THREADS = 4

# =========================================================
# DOWNLOAD DELAY
# =========================================================
# Lower = faster
# Higher = safer
# =========================================================

REQUEST_DELAY = 0.15

# =========================================================
# LOCKS
# =========================================================

counter_lock = Lock()

# =========================================================
# COUNTERS
# =========================================================

success_count = 0
failed_count = 0
skipped_count = 0

# =========================================================
# CLEAN FILENAME
# =========================================================

def clean_filename(name):

    name = str(name)

    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']

    for ch in invalid_chars:
        name = name.replace(ch, "_")

    name = name.replace(" ", "_")

    return name

# =========================================================
# FETCH DATA
# =========================================================

def fetch_vehicle_data(vehicle_filter):

    payload = {
        "start_date": START_DATE,
        "end_date": END_DATE,

        "order": "DESC",

        "row": 0,
        "osrow": 0,

        "rowperpage": 10000,
        "osrowperpage": 10000,

        "field": "in_time",

        "in_time": "00:00:00",
        "out_time": "23:59:59",

        "mall_id": 33,

        "time_type": "in_time",

        "type": "setting",

        "vehicle_number": vehicle_filter
    }

    try:

        response = session.post(
            POS_GET_URL,
            headers=HEADERS,
            json=payload,
            timeout=120
        )

        response.raise_for_status()

        data = response.json()

        results = []

        if isinstance(data, list):

            if len(data) > 0:

                first_item = data[0]

                if isinstance(first_item, dict) and "barcode" in first_item:

                    results = data

                elif isinstance(first_item, dict) and "result" in first_item:

                    results = first_item.get("result", [])

        elif isinstance(data, dict):

            results = data.get("result", [])

        return results

    except Exception as e:

        print(f"\nFAILED FETCH FOR FILTER {vehicle_filter}")
        print(e)

        return []

# =========================================================
# DOWNLOAD SINGLE IMAGE
# =========================================================

def download_image(item, vehicle_filter):

    global success_count
    global failed_count
    global skipped_count

    try:

        barcode = item.get("barcode")
        vehicle_number = item.get("vehicle_number")

        if not barcode:

            with counter_lock:
                failed_count += 1

            return

        if not vehicle_number:

            vehicle_number = barcode

        vehicle_number = str(vehicle_number).upper()

        # =====================================================
        # EXTRA SAFETY FILTER
        # =====================================================

        if vehicle_filter.upper() not in vehicle_number:

            with counter_lock:
                skipped_count += 1

            return

        safe_name = clean_filename(vehicle_number)

        # =====================================================
        # CREATE FILTER FOLDER
        # =====================================================

        filter_folder = os.path.join(ROOT_FOLDER, vehicle_filter)

        os.makedirs(filter_folder, exist_ok=True)

        file_path = os.path.join(
            filter_folder,
            f"{safe_name}.jpg"
        )

        # =====================================================
        # SKIP IF FILE EXISTS
        # =====================================================

        if os.path.exists(file_path):

            print(f"ALREADY EXISTS: {safe_name}")

            return

        print(f"DOWNLOADING [{vehicle_filter}] {safe_name}")

        # =====================================================
        # IMAGE REQUEST
        # =====================================================

        image_payload = {
            "barcode": barcode
        }

        image_response = session.post(
            DOWNLOAD_URL,
            headers=HEADERS,
            json=image_payload,
            timeout=120
        )

        image_response.raise_for_status()

        image_data = image_response.json()

        if not isinstance(image_data, dict):

            with counter_lock:
                failed_count += 1

            return

        if image_data.get("ErrCode") == "0":

            encoded_image = image_data.get("encode")

            if encoded_image:

                image_bytes = base64.b64decode(encoded_image)

                with open(file_path, "wb") as f:
                    f.write(image_bytes)

                print(f"SAVED: {file_path}")

                with counter_lock:
                    success_count += 1

            else:

                with counter_lock:
                    failed_count += 1

        else:

            with counter_lock:
                failed_count += 1

        # =====================================================
        # SAFE RATE LIMIT
        # =====================================================

        time.sleep(REQUEST_DELAY)

    except Exception as e:

        print(f"FAILED DOWNLOAD: {e}")

        with counter_lock:
            failed_count += 1

# =========================================================
# MAIN
# =========================================================

print("\n=================================================")
print("STARTING SAFE MULTI FILTER DOWNLOAD")
print("=================================================\n")

for vehicle_filter in VEHICLE_FILTERS:

    print(f"\n==============================")
    print(f"FILTER: {vehicle_filter}")
    print(f"==============================")

    results = fetch_vehicle_data(vehicle_filter)

    if not results:

        print(f"NO RESULTS FOR {vehicle_filter}")
        continue

    print(f"FOUND {len(results)} RECORDS")

    # =====================================================
    # SAFE MULTITHREAD DOWNLOAD
    # =====================================================

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:

        futures = []

        for item in results:

            future = executor.submit(
                download_image,
                item,
                vehicle_filter
            )

            futures.append(future)

        for future in as_completed(futures):

            try:
                future.result()

            except Exception as e:
                print(e)

    # =====================================================
    # SMALL GAP BETWEEN FILTERS
    # =====================================================

    print(f"WAITING BEFORE NEXT FILTER...\n")

    time.sleep(2)

# =========================================================
# SUMMARY
# =========================================================

print("\n=================================================")
print("DOWNLOAD COMPLETE")
print("=================================================")

print(f"SUCCESS : {success_count}")
print(f"FAILED  : {failed_count}")
print(f"SKIPPED : {skipped_count}")

print(f"\nROOT FOLDER:")
print(ROOT_FOLDER)