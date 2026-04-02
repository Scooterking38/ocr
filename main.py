import re
import cv2
from collections import defaultdict
from paddleocr import PaddleOCR

# --------------------------
# CONFIG
# --------------------------
IMAGE_PATH = "image.jpg"  # already rotated manually
CROP_MIDDLE = True        # crop middle 60% for better accuracy
BAD_WORDS = [
    "vat", "total", "balance", "contactless", "mastercard",
    "merchant", "aid", "pan", "change", "points", "nectar",
    "saving", "originalprice", "price reduction", "reduction",
    "new price", "old price", "sub total"
]

# --------------------------
# HELPER FUNCTIONS
# --------------------------
def crop_receipt_middle(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image {image_path}")
    h, w = img.shape[:2]
    cropped = img[int(h*0.2):int(h*0.8), 0:w]  # keep middle 60%
    cv2.imwrite("cropped.jpg", cropped)
    return "image.jpg"

def clean_item(line):
    line = re.sub(r"([A-Za-z])(\d)", r"\1 \2", line)
    line = re.sub(r"[^A-Za-z0-9\s/\.]", "", line)
    return line.strip()

def is_price(line):
    return re.fullmatch(r"\d+\.\d{2}", line)

def is_real_item(item):
    item_lower = item.lower()
    if len(item) < 3:
        return False
    if item.replace(".", "", 1).isdigit():  # skip numeric-only
        return False
    return all(bad not in item_lower for bad in BAD_WORDS)

def box_center_y(box):
    return sum(pt[1] for pt in box) / len(box)

# --------------------------
# OCR
# --------------------------
ocr = PaddleOCR(use_angle_cls=True, lang='en')

if CROP_MIDDLE:
    IMAGE_PATH = crop_receipt_middle(IMAGE_PATH)

result = ocr.ocr(IMAGE_PATH, cls=True)

ocr_data = []
for line in result[0]:
    box, (text, score) = line
    ocr_data.append({"box": box, "text": text, "score": score})

# Sort lines top-to-bottom
lines = [x["text"].strip() for x in sorted(ocr_data, key=lambda b: box_center_y(b["box"])) if x["text"].strip()]

# Remove garbage lines
lines = [
    l for l in lines
    if l.strip() and not l.strip().lower().startswith((
        "www.", "pan sequence", "merchant:", "aid:", "debit", "contactless", "balance due"
    ))
]

print("OCR TEXT:")
for l in lines:
    print(l)

# --------------------------
# EXTRACT ITEMS
# --------------------------
items = []
i = 0
while i < len(lines):
    line = clean_item(lines[i])

    # ITEM then PRICE
    if i+1 < len(lines) and is_price(lines[i+1]):
        price = float(lines[i+1])
        if is_real_item(line):
            items.append({"item": line, "price": price})
        i += 2
        continue

    # ITEM then ORIGINAL PRICE
    if i+1 < len(lines) and "original" in lines[i+1].lower():
        m = re.search(r"\d+\.\d{2}", lines[i+1])
        if m:
            price = float(m.group())
            if is_real_item(line):
                items.append({"item": line, "price": price})
            i += 2
            continue

    i += 1

# --------------------------
# DETECT SHOP
# --------------------------
shop = "Unknown"
for l in lines:
    if "sainsbury" in l.lower(): shop = "Sainsbury's"
    elif "tesco" in l.lower(): shop = "Tesco"
    elif "aldi" in l.lower(): shop = "Aldi"
    elif "lidl" in l.lower(): shop = "Lidl"

print("\nDETECTED ITEMS:")
for it in items:
    print(it)

# --------------------------
# COMBINE DUPLICATES
# --------------------------
item_summary = defaultdict(lambda: {"qty": 0, "price": 0.0})

for it in items:
    key = it["item"]
    item_summary[key]["qty"] += 1
    item_summary[key]["price"] = it["price"]  # assume same price per item

# --------------------------
# WRITE CSV
# --------------------------
with open("receipt.csv", "w") as f:
    f.write("Shop,Item,Qty,Price,Total\n")
    for item, data in item_summary.items():
        total = data["qty"] * data["price"]
        f.write(f"{shop},{item},{data['qty']},{data['price']:.2f},{total:.2f}\n")

print("\nCSV OUTPUT:")
with open("receipt.csv") as f:
    print(f.read())
