import json
import re
import subprocess
from paddleocr import PaddleOCR

# Initialize OCR
ocr = PaddleOCR(use_angle_cls=True, lang='en')

image_path = "image.jpg"
result = ocr.ocr(image_path, cls=True)

# Flatten OCR results
ocr_data = []
for line in result[0]:
    box = line[0]
    text = line[1][0]
    score = line[1][1]
    ocr_data.append({"box": box, "text": text, "score": score})

# Get vertical center
def box_center_y(box):
    ys = [pt[1] for pt in box]
    return sum(ys) / len(ys)

# Sort top-to-bottom
ocr_data_sorted = sorted(ocr_data, key=lambda b: box_center_y(b["box"]))

# Merge text
lines = [x["text"].strip() for x in ocr_data_sorted if x["text"].strip()]

print("OCR TEXT:")
for l in lines:
    print(l)

# --------------------------
# RULE-BASED ITEM EXTRACTION
# --------------------------

def is_price(line):
    return re.fullmatch(r"\d+\.\d{2}", line)

def clean_item(line):
    return re.sub(r"[^A-Za-z0-9\s/\.]", "", line).strip()

items = []
i = 0

while i < len(lines):
    line = lines[i]

    # Price on next line
    if i + 1 < len(lines) and is_price(lines[i + 1]):
        item = clean_item(line)
        price = float(lines[i + 1])

        if len(item) > 2 and not any(x in item.lower() for x in [
            "vat", "total", "balance", "contactless",
            "mastercard", "merchant", "aid", "pan",
            "change", "points", "nectar", "saving"
        ]):
            items.append({"item": item, "price": price})

        i += 2
        continue

    # Price on same line
    match = re.match(r"(.+?)\s+(\d+\.\d{2})$", line)
    if match:
        item = clean_item(match.group(1))
        price = float(match.group(2))
        items.append({"item": item, "price": price})

    i += 1

# Detect shop
shop = "Unknown"
for l in lines:
    if "sainsbury" in l.lower():
        shop = "Sainsbury's"
    elif "tesco" in l.lower():
        shop = "Tesco"
    elif "aldi" in l.lower():
        shop = "Aldi"
    elif "lidl" in l.lower():
        shop = "Lidl"

print("\nDETECTED ITEMS:")
for it in items:
    print(it)

# --------------------------
# SEND CLEAN DATA TO OLLAMA
# --------------------------

structured_text = "\n".join([f"{it['item']} - {it['price']}" for it in items])

prompt = f"""
Convert this list into CSV.

Shop: {shop}

Items:
{structured_text}

Output ONLY CSV with columns:
Shop,Item,Price
"""

result = subprocess.run(
    ["ollama", "run", "llama2"],
    input=prompt.encode(),
    stdout=subprocess.PIPE
)

csv_output = result.stdout.decode()

with open("receipt.csv", "w") as f:
    f.write(csv_output)

print("\nCSV OUTPUT:")
print(csv_output)
