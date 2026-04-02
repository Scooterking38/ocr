# --------------------------
# Dockerfile for PaddleOCR 3.0 + Selenium + try.py
# --------------------------
FROM python:3.10-slim

# --------------------------
# ENVIRONMENT VARIABLES
# --------------------------
ENV PIP_NO_CACHE_DIR=off \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    CHROME_BIN=/usr/bin/google-chrome-stable \
    CHROMEDRIVER_BIN=/usr/bin/chromedriver

# --------------------------
# INSTALL SYSTEM DEPENDENCIES
# --------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    unzip \
    git \
    build-essential \
    python3-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgtk2.0-dev \
    libnss3 \
    libgconf-2-4 \
    ca-certificates \
    fonts-liberation \
    xvfb \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# --------------------------
# INSTALL CHROME AND CHROMEDRIVER
# --------------------------
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && CHROME_VERSION=$(google-chrome --version | grep -oP "\d+\.\d+\.\d+") \
    && wget -q "https://chromedriver.storage.googleapis.com/${CHROME_VERSION}/chromedriver_linux64.zip" \
    && unzip chromedriver_linux64.zip -d /usr/bin/ \
    && chmod +x /usr/bin/chromedriver \
    && rm chromedriver_linux64.zip

# --------------------------
# SET WORKDIR
# --------------------------
WORKDIR /app

# --------------------------
# COPY SCRIPT
# --------------------------
COPY try.py /app/try.py

# --------------------------
# INSTALL PYTHON DEPENDENCIES
# --------------------------
RUN pip install --upgrade pip setuptools wheel
RUN pip install \
    paddleocr==3.0.0 \
    paddlepaddle \
    opencv-python-headless \
    numpy \
    requests \
    beautifulsoup4 \
    selenium \
    urllib3

# --------------------------
# ENTRYPOINT
# --------------------------
CMD ["python", "try.py"]
