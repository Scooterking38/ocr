# Base image
FROM paddlepaddle/paddle:3.3.0

# Environment variables
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PIP_NO_CACHE_DIR=1

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

# --------------------------
# Install Python packages in the correct order
# --------------------------
# 1. Upgrade pip
RUN pip install --upgrade pip

# 2. Install a compatible numpy first
RUN pip install numpy==1.25.2

# 3. Install OpenCV and other dependencies
RUN pip install opencv-python-headless==4.8.1.78 paddleocr==2.7.0.1 python-Levenshtein

# --------------------------
# Set working directory
# --------------------------
WORKDIR /workspace

# --------------------------
# Copy project files
# --------------------------
COPY . /workspace

# --------------------------
# Default command
# --------------------------
CMD ["python", "try.py"]
