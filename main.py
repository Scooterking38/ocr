import re
import cv2
import numpy as np
from paddleocr import PaddleOCR

# --------------------------
# IMAGE PREPROCESSING
# --------------------------
def auto_rotate(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
    if lines is not None:
        angles = [(theta * 180 / np.pi) - 90 for rho, theta in lines[:,0]]
        median_angle = np.median(angles)
        (h, w) = img.shape[:2]
        M = cv2.getRotationMatrix2D((w//2, h//2), median_angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        cv2.imwrite("rotated.jpg", rotated)
        return "rotated.jpg"
    return image_path

def crop_receipt_middle(image_path):
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    cropped = img[int(h*0.2):int(h*0.8), 0:w]
    cv2.imwrite("cropped.jpg", cropped)
    return "cropped.jpg"

# --------------------------
# OCR
# --------------------------
ocr = PaddleOCR(use_angle_cls=True, lang='en')

image_path = "image.jpg"
image_path = auto_rotate(image_path)
image_path = crop_receipt_middle(image_path)

result = ocr.ocr(image_path, cls=True)

ocr_data = []
for line in result[0]:
    box, (text, score) = line
    ocr_data.append({"box": box, "text": text, "score": score})

def box_center_y(box):
    return sum(pt[1] for pt in box) / len(box)

lines = [x["text"].strip() for x in sorted(ocr_data, key=lambda b: box_center_y(b["box"])) if x["text"].strip()]

print("OCR TEXT:")
for l in lines:
    print(l)

# --------------------------
# CLEAN AND EXTRACT ITEMS
# --------------------------
def clean_item(line):
    line = re.sub(r"([A-Za-z])(\d)", r"\1 \2", line)
    line = re.sub(r"[^A-Za-z0-9\s/\.]", "", line)
    return line.strip()

def is_price(line):
    return re.fullmatch(r"\d+\.\d{2}", line)

BAD_WORDS = [
    "vat", "total", "balance", "contactless", "mastercard",
    "merchant", "aid", "pan", "change", "points", "nectar",
    "saving", "originalprice", "price reduction", "reduction",
    "new price", "old price", "sub total"
]

def is_real_item(item):
    item_lower = item.lower()
    if len(item) < 3:
        return False
    return all(bad not in item_lower for bad in BAD_WORDS)

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
# WRITE CSV
# --------------------------
with open("receipt.csv", "w") as f:
    f.write("Shop,Item,Price\n")
    for it in items:
        f.write(f"{shop},{it['item']},{it['price']:.2f}\n")

print("\nCSV OUTPUT:")
with open("receipt.csv") as f:
    print(f.read())
