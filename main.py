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
Extract shop name, items and prices from this receipt.
Return ONLY CSV format with columns: Shop,Item,Price.

Receipt:
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
