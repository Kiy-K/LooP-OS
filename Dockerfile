FROM ubuntu:22.04

# Prevent interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive

# --- System dependencies ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    wget curl ca-certificates git \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libasound2 libpangocairo-1.0-0 libpango-1.0-0 \
    libcairo2 libxshmfence1 libglib2.0-0 libgbm1 libx11-xcb1 \
    libx11-6 libxext6 libxss1 fonts-unifont xvfb \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Python requirements ---
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# --- Playwright (fast on Ubuntu) ---
RUN pip3 install playwright==1.41.2
RUN playwright install-deps chromium
RUN playwright install chromium

# --- FyodorOS files ---
COPY . /app
WORKDIR /app
EXPOSE 7860

CMD ["python3", "fyodoros.py"]
# --- IGNORE ---