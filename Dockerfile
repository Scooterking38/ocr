# --------------------------
# PaddleOCR 3.0 + Selenium + try.py
# --------------------------
FROM python:3.10-slim

ENV PIP_NO_CACHE_DIR=off \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    CHROME_BIN=/usr/bin/google-chrome-stable \
    CHROMEDRIVER_BIN=/usr/bin/chromedriver

# --------------------------
# SYSTEM DEPENDENCIES
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
    ca-certificates \
    fonts-liberation \
    xvfb \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# --------------------------
# INSTALL CHROME
# --------------------------
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# --------------------------
# INSTALL CHROMEDRIVER
# --------------------------
RUN CHROME_VERSION=$(google-chrome --version | grep -oP "\d+\.\d+\.\d+") \
    && wget -q "https://chromedriver.storage.googleapis.com/${CHROME_VERSION}/chromedriver_linux64.zip" \
    && unzip chromedriver_linux64.zip -d /usr/bin/ \
    && chmod +x /usr/bin/chromedriver \
    && rm chromedriver_linux64.zip

# --------------------------
# WORKDIR AND SCRIPT
# --------------------------
WORKDIR /app
COPY try.py /app/try.py

# --------------------------
# PYTHON DEPENDENCIES
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
