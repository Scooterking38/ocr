import json
from paddleocr import PaddleOCR
import ollama
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
    flat = []
    for b in box:
        if isinstance(b, list):
            flat.extend(b)
        else:
            flat.append(b)
    y_coords = flat[1::2]
    return sum(y_coords) / len(y_coords)

# Function to get min X (for left-to-right sorting)
def box_min_x(box):
    flat = []
    for b in box:
        if isinstance(b, list):
            flat.extend(b)
        else:
            flat.append(b)
    x_coords = flat[0::2]
    return min(x_coords)

# Sort OCR data top-to-bottom, then left-to-right
ocr_data_sorted = sorted(
    ocr_data,
    key=lambda b: (box_center_y(b["box"]), box_min_x(b["box"]))
)

# Combine text in reading order
receipt_text = "\n".join([entry["text"] for entry in ocr_data_sorted])

# Save OCR output for inspection
with open("ocr_results_ordered.txt", "w") as f:
    f.write(receipt_text)

# --- Use Ollama LLM to parse items ---

prompt = f"""
Extract purchased items from this receipt.

Return ONLY valid CSV.
No explanations.

Format exactly:
Item,Price,Shop

Rules:
- Only include real purchased items
- Ignore totals, dates, IDs
- Price must be numeric

OCR text:
{receipt_text}
"""

# Call Ollama (new API)
response = ollama.chat(
    model="llama2",  # change if needed (e.g., llama3)
    messages=[
        {"role": "user", "content": prompt}
    ]
)

csv_text = response["message"]["content"].strip()

# Save CSV
with open("receipt_items.csv", "w") as f:
    f.write(csv_text)

print("OCR text saved to ocr_results_ordered.txt")
print("CSV extracted to receipt_items.csv")
print(csv_text)
