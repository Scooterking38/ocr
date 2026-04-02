import re
import cv2
import numpy as np
from paddleocr import PaddleOCR
from difflib import SequenceMatcher
from pathlib import Path

# NEW IMPORTS
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --------------------------
# CONFIG
# --------------------------
BASE_URL = "https://aragonindustries.uk/photos"
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
# FETCH IMAGES FROM SITE
# --------------------------
def fetch_image_urls():
    res = requests.get(BASE_URL, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "html.parser")

    urls = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if src and (".jpg" in src or ".png" in src):
            urls.append(urljoin(BASE_URL, src))

    return urls


def load_image_from_url(url):
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, verify=False)
    img_array = np.frombuffer(resp.content, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return img

# --------------------------
# PREPROCESSING FUNCTIONS
# --------------------------
def preprocess_image_from_array(img, max_width=1024):
    if img is None:
        raise ValueError("Invalid image")

    if img.shape[1] > max_width:
        scale = max_width / img.shape[1]
        img = cv2.resize(img, (max_width, int(img.shape[0] * scale)))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    if np.mean(thresh) > 127:
        thresh = 255 - thresh

    coords = np.column_stack(np.where(thresh < 255))
    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    (h, w) = thresh.shape
    M = cv2.getRotationMatrix2D((w // 2, h // 2), -angle, 1.0)

    deskewed = cv2.warpAffine(
        thresh, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )

    return deskewed

# --------------------------
# OCR FUNCTIONS
# --------------------------
ocr = PaddleOCR(use_angle_cls=True, lang='en')

def extract_lines(img):
    result = ocr.ocr(img, cls=True)
    ocr_data = []
    for line in result[0]:
        box, (text, score) = line
        ocr_data.append({"box": box, "text": text.strip(), "score": score})
    ocr_data_sorted = sorted(ocr_data, key=lambda b: sum(pt[1] for pt in b["box"]) / len(b["box"]))
    return [x["text"] for x in ocr_data_sorted if x["text"]]

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
    return merged

# --------------------------
# PROCESS ALL IMAGES
# --------------------------
all_items = []

image_urls = fetch_image_urls()

for url in image_urls:
    print(f"\nProcessing {url} ...")

    img = load_image_from_url(url)
    preprocessed_img = preprocess_image_from_array(img)

    lines = extract_lines(preprocessed_img)
    items = extract_items(lines)
    all_items.extend(items)

merged_items = merge_duplicates(all_items)

# Build CSV content
csv_content = "Item,Qty,Price,Total\n"
for m in merged_items:
    csv_content += f"{m['item']},{m['qty']},{m['price']:.2f},{m['total']:.2f}\n"

# Write to file
with open(OUTPUT_CSV, "w") as f:
    f.write(csv_content)

# Print to console
print(csv_content)

print(f"\n✅ All images processed. CSV saved as {OUTPUT_CSV}")
