# Use PaddleOCR prebuilt image
FROM paddleocr/paddleocr:latest

# Set working directory
WORKDIR /workspace

# Copy your OCR script
COPY main.py .

# Default command
CMD ["python", "main.py"]
