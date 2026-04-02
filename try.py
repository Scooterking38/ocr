import re
import cv2
import numpy as np
from paddleocr import PaddleOCR
from difflib import SequenceMatcher
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --------------------------
# CONFIG
# --------------------------
BASE_URL = "http://aragonindustries.uk/photos/"
OUTPUT_DIR = Path("aragonindustries.uk/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_CSV = OUTPUT_DIR / "all_receipts.csv"

BAD_WORDS = [
    "vat", "total", "balance", "contactless", "mastercard",
    "merchant", "aid", "pan", "change", "points", "nectar",
    "saving", "originalprice", "price reduction", "reduction",
    "new price", "old price", "sub total", "www."
]

CORRECTIONS = {}

# --------------------------
# FETCH IMAGES
# --------------------------
def fetch_image_urls():
    print(f"[INFO] Fetching image URLs from {BASE_URL}")
    try:
        res = requests.get(BASE_URL, headers={"User-Agent": "Mozilla/5.0"}, verify=False)
        print(f"[INFO] HTTP status code: {res.status_code}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch {BASE_URL}: {e}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    urls = []

    for img in soup.find_all("img"):
        src = img.get("src")
        if src and (".jpg" in src.lower() or ".png" in src.lower()):
            full_url = urljoin(BASE_URL, src)
            urls.append(full_url)
            print(f"[FOUND] Image URL: {full_url}")

    if not urls:
        print("[WARN] No images found on page!")

    return urls


def load_image_from_url(url):
    print(f"[INFO] Downloading image: {url}")
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, verify=False)
        img_array = np.frombuffer(resp.content, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            print(f"[WARN] Failed to decode image: {url}")
        return img
    except Exception as e:
        print(f"[ERROR] Could not load image {url}: {e}")
        return None

# --------------------------
# PREPROCESSING
# --------------------------
def preprocess_image_from_array(img, max_width=1024):
    if img is None:
        raise ValueError("Invalid image")

    print(f"[INFO] Preprocessing image (original shape: {img.shape})")
    if img.shape[1] > max_width:
        scale = max_width / img.shape[1]
        img = cv2.resize(img, (max_width, int(img.shape[0] * scale)))
        print(f"[INFO] Resized image to {img.shape}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    if np.mean(thresh) > 127:
        thresh = 255 - thresh

    coords = np.column_stack(np.where(thresh < 255))
    if coords.size == 0:
        print("[WARN] No text detected, skipping deskew")
        return thresh

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    (h, w) = thresh.shape
    M = cv2.getRotationMatrix2D((w // 2, h // 2), -angle, 1.0)
    deskewed = cv2.warpAffine(thresh, M, (w, h),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)
    print(f"[INFO] Deskewed image by {angle:.2f} degrees")
    return deskewed

# --------------------------
# OCR
# --------------------------
ocr = PaddleOCR(use_angle_cls=True, lang='en')

def extract_lines(img):
    print("[INFO] Running OCR...")
    result = ocr.ocr(img, cls=True)
    ocr_data = []

    for line in result[0]:
        box, (text, score) = line
        text = text.strip()
        if text:
            ocr_data.append({"box": box, "text": text, "score": score})

    print(f"[INFO] OCR detected {len(ocr_data)} lines")
    ocr_data_sorted = sorted(ocr_data, key=lambda b: sum(pt[1] for pt in b["box"]) / len(b["box"]))
    return [x["text"] for x in ocr_data_sorted]

# --------------------------
# ITEM EXTRACTION
# --------------------------
def clean_item(line):
    line = re.sub(r"([A-Za-z])(\d)", r"\1 \2", line)
    line = re.sub(r"[^A-Za-z0-9\s/\.]", "", line)
    return line.strip()

def is_price(line):
    return re.fullmatch(r"\d+\.\d{2}", line)

def is_real_item(item):
    item_lower = item.lower()
    if len(item) < 3 or item.replace(".", "", 1).isdigit():
        return False
    return all(bad not in item_lower for bad in BAD_WORDS)

def extract_items(lines):
    items = []
    for i, line in enumerate(lines):
        clean_line = clean_item(line)
        if is_price(clean_line) and float(clean_line) > 0:
            j = i - 1
            while j >= 0:
                candidate = clean_item(lines[j])
                if is_real_item(candidate):
                    items.append({"item": candidate, "price": float(clean_line)})
                    break
                j -= 1
    print(f"[INFO] Extracted {len(items)} items from OCR lines")
    for it in items:
        if it["item"] in CORRECTIONS:
            it["item"] = CORRECTIONS[it["item"]]
    return items

# --------------------------
# MERGE DUPLICATES
# --------------------------
def merge_duplicates(items):
    merged = []
    for it in items:
        matched = False
        for m in merged:
            if SequenceMatcher(None, it["item"], m["item"]).ratio() > 0.9:
                m["qty"] += 1
                m["total"] += it["price"]
                matched = True
                break
        if not matched:
            merged.append({"item": it["item"], "qty": 1, "price": it["price"], "total": it["price"]})
    print(f"[INFO] Merged into {len(merged)} unique items")
    return merged

# --------------------------
# MAIN PROCESS
# --------------------------
all_items = []

image_urls = fetch_image_urls()
print(f"[INFO] Total images found: {len(image_urls)}")

for url in image_urls:
    print(f"\n[PROCESSING] {url}")
    img = load_image_from_url(url)
    if img is None:
        print(f"[WARN] Skipping {url}")
        continue

    preprocessed_img = preprocess_image_from_array(img)
    lines = extract_lines(preprocessed_img)
    items = extract_items(lines)
    all_items.extend(items)

merged_items = merge_duplicates(all_items)

# --------------------------
# CSV OUTPUT
# --------------------------
csv_content = "Item,Qty,Price,Total\n"
for m in merged_items:
    csv_content += f"{m['item']},{m['qty']},{m['price']:.2f},{m['total']:.2f}\n"

with open(OUTPUT_CSV, "w") as f:
    f.write(csv_content)

print("\n[INFO] CSV content:")
print(csv_content)
print(f"\n✅ All images processed. CSV saved as {OUTPUT_CSV}")
