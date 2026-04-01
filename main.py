FROM paddlepaddle/paddle:3.3.0

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama via apt repo
RUN curl -fsSL https://ollama.com/install.sh | sh || true

# Install compatible NumPy first
RUN pip install --no-cache-dir --upgrade numpy==1.26.2

# Install Python packages
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

# Expose Ollama port
EXPOSE 11434

# Start Ollama, wait, pull model, then run script
CMD bash -c "\
    ollama serve & \
    echo 'Waiting for Ollama...' && \
    sleep 15 && \
    ollama pull phi3 && \
    python main.py image.jpg image2.jpg \
"
