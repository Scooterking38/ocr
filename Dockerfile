# Use PaddleOCR prebuilt image
FROM paddlepaddle/paddle:3.3.0

# Set working directory
WORKDIR /workspace

# Copy your OCR script
COPY main.py .

# Default command
CMD ["python", "main.py"]
