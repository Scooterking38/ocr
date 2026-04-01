FROM paddlepaddle/paddle:3.3.0

WORKDIR /workspace

# Install a compatible NumPy version first
RUN pip install --no-cache-dir --upgrade numpy==1.26.2

# Then install all other Python packages
RUN pip install --no-cache-dir \
    paddleocr==2.7.0.3 \
    opencv-python-headless==4.6.0.66 \
    PyMuPDF \
    pandas \
    matplotlib \
    tqdm \
    pillow \
    scikit-image \
    requests \
    python-docx \
    rapidfuzz \
    pdf2docx \
    beautifulsoup4 \
    ollama

# Copy project files
COPY . /workspace
CMD ["ollama", "serve"]
CMD ["python", "main.py", "image.jpg", "image2.jpg"]
