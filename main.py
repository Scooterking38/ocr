# main.py
import re
import cv2
import numpy as np
from paddleocr import PaddleOCR
from difflib import SequenceMatcher
from pathlib import Path

INPUT_DIR = Path("aragonindustries.uk/photos")
OUTPUT_DIR = Path("aragonindustries.uk/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_CSV = OUTPUT_DIR / "all_receipts.csv"

BAD_WORDS = ["vat", "total", "balance", "contactless", "mastercard",
             "merchant", "aid", "pan", "change", "points", "nectar",
             "saving", "originalprice", "price reduction", "reduction",
             "new price", "old price", "sub total", "www."]

CORRECTIONS = {
    "TSUES": "JS RED PEPPER SINGLE",
    "SHEETS": "JS RED PEPPER SINGLE",
    "*VIMTO": "VIMTO",
    "JS S/SKIM MLK2.272L": "JS S/SKIM MLK 2.272L"
}

def preprocess_image(path, max_width=1024):
    img = cv2.imread(str(path))
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
    return cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

ocr = PaddleOCR(use_angle_cls=True, lang='en')

def extract_lines(img):
    result = ocr.ocr(img, cls=True)
    ocr_data = []
    for line in result[0]:
        box, (text, score) = line
        ocr_data.append({"box": box, "text": text.strip(), "score": score})
    ocr_data_sorted = sorted(ocr_data, key=lambda b: sum(pt[1] for pt in b["box"]) / len(b["box"]))
    return [x["text"] for x in ocr_data_sorted if x["text"]]

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

all_items = []
for img_file in INPUT_DIR.glob("*.[jp][pn]g"):
    print(f"Processing {img_file.name} ...")
    preprocessed_img = preprocess_image(img_file)
    lines = extract_lines(preprocessed_img)
    items = extract_items(lines)
    all_items.extend(items)

merged_items = merge_duplicates(all_items)

with open(OUTPUT_CSV, "w") as f:
    f.write("Item,Qty,Price,Total\n")
    for m in merged_items:
        f.write(f"{m['item']},{m['qty']},{m['price']:.2f},{m['total']:.2f}\n")

print(f"\n✅ All images processed. CSV saved as {OUTPUT_CSV}")
