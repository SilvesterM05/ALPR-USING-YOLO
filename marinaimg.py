import requests
import base64
import os
import time
import json
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================================================
# CONFIG
# =========================================================

START_DATE = "2026-05-11"
END_DATE   = "2026-05-11"

VEHICLE_FILTERS = [
    "O","Y","N"
]

POS_GET_URL = "https://themarinamall.random-mouse.com/ops/pos_get"

DOWNLOAD_URL = "https://themarinamall.random-mouse.com/ops/download_image"

HEADERS = {
    "accept": "application/json, text/plain, */*",

    "content-type": "application/json;charset=UTF-8",

    "origin": "https://themarinamall.random-mouse.com",

    "referer": "https://themarinamall.random-mouse.com/sysadmin/",

    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36"
    ),

    "AccessToken": "7a345367784255694e794135364647456c54524d4b7548717742746e6d396238356a4c79353645611",

    "AuthCode": "744e674466615267786e356658736538"
}

COOKIES = {
    "token": "7a345367784255694e794135364647456c54524d4b7548717742746e6d396238356a4c79353645611"
}

ROOT_FOLDER = f"marina_mall_downloads_{START_DATE}_to_{END_DATE}"

os.makedirs(ROOT_FOLDER, exist_ok=True)

session = requests.Session()

MAX_THREADS = 5

REQUEST_DELAY = 0.10

counter_lock = Lock()

success_count = 0
failed_count = 0

# =========================================================
# CLEAN FILE NAME
# =========================================================

def clean_filename(name):

    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']

    for ch in invalid_chars:
        name = name.replace(ch, "_")

    return name.replace(" ", "_")

# =========================================================
# FETCH ALL DATA
# =========================================================

def fetch_all_data():

    payload = {
        "start_date": START_DATE,
        "end_date": END_DATE,

        "order": "DESC",
        "osorder": "DESC",

        "row": 0,
        "osrow": 0,

        "rowperpage": 10000,
        "osrowperpage": 10000,

        "field": "in_time",

        "in_time": "00:00:00",
        "out_time": "23:59:59",

        "mall_id": 34,

        "time_type": "in_time",

        "type": "setting"
    }

    try:

        print("\n================================================")
        print("FETCHING ALL DATA")
        print("================================================")

        response = session.post(
            POS_GET_URL,
            headers=HEADERS,
            cookies=COOKIES,
            json=payload,
            timeout=120,
            verify=False
        )

        print(f"\nSTATUS CODE : {response.status_code}")

        response.raise_for_status()

        data = response.json()

        results = data.get("result", [])

        print(f"\nTOTAL RECORDS : {len(results)}")

        return results

    except Exception as e:

        print("\nFAILED FETCH")
        print(e)

        return []

# =========================================================
# DOWNLOAD IMAGE
# =========================================================

def download_image(item, vehicle_filter):

    global success_count
    global failed_count

    try:

        barcode = item.get("barcode")

        vehicle_number = item.get("vehicle_number")

        if not barcode or not vehicle_number:
            return

        vehicle_number = str(vehicle_number).upper()

        if vehicle_filter.upper() not in vehicle_number:
            return

        filter_folder = os.path.join(
            ROOT_FOLDER,
            vehicle_filter
        )

        os.makedirs(filter_folder, exist_ok=True)

        safe_name = clean_filename(vehicle_number)

        file_path = os.path.join(
            filter_folder,
            f"{safe_name}.jpg"
        )

        if os.path.exists(file_path):

            print(f"ALREADY EXISTS : {safe_name}")
            return

        print(f"DOWNLOADING [{vehicle_filter}] {safe_name}")

        image_payload = {
            "barcode": barcode
        }

        image_response = session.post(
            DOWNLOAD_URL,
            headers=HEADERS,
            cookies=COOKIES,
            json=image_payload,
            timeout=120,
            verify=False
        )

        image_response.raise_for_status()

        image_data = image_response.json()

        if image_data.get("ErrCode") == "0":

            encoded_image = image_data.get("encode")

            if encoded_image:

                image_bytes = base64.b64decode(encoded_image)

                with open(file_path, "wb") as f:
                    f.write(image_bytes)

                print(f"SAVED : {file_path}")

                with counter_lock:
                    success_count += 1

        time.sleep(REQUEST_DELAY)

    except Exception as e:

        print(f"FAILED DOWNLOAD : {e}")

        with counter_lock:
            failed_count += 1

# =========================================================
# MAIN
# =========================================================

print("\n=================================================")
print("STARTING MARINA MALL DOWNLOAD")
print("=================================================\n")

all_results = fetch_all_data()

for vehicle_filter in VEHICLE_FILTERS:

    print(f"\n==============================")
    print(f"FILTER : {vehicle_filter}")
    print(f"==============================")

    filtered_results = []

    for item in all_results:

        vehicle_number = str(
            item.get("vehicle_number", "")
        ).upper()

        if vehicle_filter.upper() in vehicle_number:
            filtered_results.append(item)

    print(f"FOUND {len(filtered_results)} RECORDS")

    if not filtered_results:
        continue

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:

        futures = []

        for item in filtered_results:

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

print("\n=================================================")
print("DOWNLOAD COMPLETE")
print("=================================================")

print(f"SUCCESS : {success_count}")
print(f"FAILED  : {failed_count}")

print(f"\nROOT FOLDER:")
print(ROOT_FOLDER)