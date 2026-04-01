import json
from paddleocr import PaddleOCR
from ollama import Ollama
import pandas as pd

# Initialize PaddleOCR (English)
ocr = PaddleOCR(use_angle_cls=True, lang='en')

# Path to receipt image
image_path = "image.jpg"

# Run OCR
result = ocr.ocr(image_path, cls=True)

# Flatten OCR results into a list of dicts
ocr_data = []
for line in result[0]:
    box = line[0]
    text = line[1][0]
    score = line[1][1]
    ocr_data.append({"box": box, "text": text, "score": score})

# Function to get box center Y
def box_center_y(box):
    # Flatten coordinates in case nested lists appear
    flat = []
    for b in box:
        if isinstance(b, list):
            flat.extend(b)
        else:
            flat.append(b)
    y_coords = flat[1::2]
    return sum(y_coords) / len(y_coords)

# Sort OCR data top-to-bottom, then left-to-right
ocr_data_sorted = sorted(
    ocr_data,
    key=lambda b: (box_center_y(b["box"]), min(coord for i, coord in enumerate(b["box"]) if i % 2 == 0))
)

# Combine text in reading order
receipt_text = "\n".join([entry["text"] for entry in ocr_data_sorted])

# Save for inspection
with open("ocr_results_ordered.txt", "w") as f:
    f.write(receipt_text)

# --- Use Ollama LLM to parse items ---
model = Ollama(model="llama2")  # replace with your local model name

prompt = f"""
You are a receipt parser. Extract the following details in CSV format:
- Item name
- Price
- Shop name (if present)

Only include lines that are actual purchased items with prices.
Output CSV with columns: Item,Price,Shop
OCR text:
{receipt_text}
"""

response = model.chat(prompt)
csv_text = response.text.strip()

# Save CSV
with open("receipt_items.csv", "w") as f:
    f.write(csv_text)

print("OCR text saved to ocr_results_ordered.txt")
print("CSV extracted to receipt_items.csv")
print(csv_text)
