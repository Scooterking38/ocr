import json
from paddleocr import PaddleOCR
import subprocess

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
receipt_text = "\n".join([x["text"] for x in ocr_data_sorted])

with open("ocr_text.txt", "w") as f:
    f.write(receipt_text)

print("OCR TEXT:")
print(receipt_text)

# Send to Ollama
prompt = f"""
You are a system that extracts purchased items from supermarket receipts.

Rules:
- Only include actual purchased products.
- Each product has a name and a price.
- Ignore payment info (Mastercard, Contactless, PAN, AID, Merchant, VAT, Balance Due, etc.).
- Ignore discounts unless they are attached to an item.
- Ignore totals, subtotal, VAT, change, points, nectar, etc.
- The shop name is usually at the bottom (e.g., Sainsbury's, Tesco, Aldi, Lidl).
- If multiple identical items appear, include them as separate rows.
- Output ONLY CSV.
- Do NOT include explanations.
- Do NOT include code blocks.
- CSV columns must be exactly: Shop,Item,Price

Receipt text:
{receipt_text}
"""

result = subprocess.run(
    ["ollama", "run", "llama2"],
    input=prompt.encode(),
    stdout=subprocess.PIPE
)

csv_output = result.stdout.decode()

with open("receipt.csv", "w") as f:
    f.write(csv_output)

print("CSV OUTPUT:")
print(csv_output)
