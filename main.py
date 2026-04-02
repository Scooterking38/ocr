import re
import subprocess
from paddleocr import PaddleOCR

# --------------------------
# OCR
# --------------------------
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

# Get vertical center of box
def box_center_y(box):
    ys = [pt[1] for pt in box]
    return sum(ys) / len(ys)

# Sort text top-to-bottom
ocr_data_sorted = sorted(ocr_data, key=lambda b: box_center_y(b["box"]))

# Clean and collect lines
def clean_item(line):
    line = re.sub(r"([A-Za-z])(\d)", r"\1 \2", line)  # MLK2.272L → MLK 2.272L
    line = re.sub(r"[^A-Za-z0-9\s/\.]", "", line)
    return line.strip()

lines = [x["text"].strip() for x in ocr_data_sorted if x["text"].strip()]

print("OCR TEXT:")
for l in lines:
    print(l)

# --------------------------
# PARSE ITEMS
# --------------------------

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
    for bad in BAD_WORDS:
        if bad in item_lower:
            return False
    return True

items = []
i = 0

while i < len(lines):
    line = clean_item(lines[i])

    # Case 1: item then price
    if i + 1 < len(lines) and is_price(lines[i + 1]):
        price = float(lines[i + 1])
        if is_real_item(line):
            items.append({"item": line, "price": price})
        i += 2
        continue

    # Case 2: item then ORIGINAL PRICE 1.80
    if (
        i + 1 < len(lines)
        and "original" in lines[i + 1].lower()
        and re.search(r"\d+\.\d{2}", lines[i + 1])
    ):
        price = float(re.search(r"\d+\.\d{2}", lines[i + 1]).group())
        if is_real_item(line):
            items.append({"item": line, "price": price})
        i += 2
        continue

    # Case 3: item and price on same line
    match = re.match(r"(.+?)\s+(\d+\.\d{2})$", line)
    if match:
        item = clean_item(match.group(1))
        price = float(match.group(2))
        if is_real_item(item):
            items.append({"item": item, "price": price})

    i += 1

# --------------------------
# DETECT SHOP
# --------------------------

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
Convert this into CSV.

Shop: {shop}

Items:
{structured_text}

Output ONLY raw CSV.
No sentences.
No explanations.
No markdown.
Columns must be:
Shop,Item,Price
"""

result = subprocess.run(
    ["ollama", "run", "llama2", "--temperature", "0"],
    input=prompt.encode(),
    stdout=subprocess.PIPE
)

csv_output = result.stdout.decode()

with open("receipt.csv", "w") as f:
    f.write(csv_output)

print("\nCSV OUTPUT:")
print(csv_output)
