FROM ubuntu:jammy

ENV DEBIAN_FRONTEND=noninteractive

# Install System Dependencies for Remastering and Building
RUN apt-get update && apt-get install -y \
    squashfs-tools \
    xorriso \
    p7zip-full \
    mtools \
    dosfstools \
    wget \
    curl \
    git \
    sudo \
    sed \
    file \
    build-essential \
    libwebkit2gtk-4.0-dev \
    libssl-dev \
    libgtk-3-dev \
    appstream \
    python3-pip \
    python3-venv \
    python3-dev \
    patchelf \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22.x (Required for Vite 7+)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g pnpm

# Install Rust (Stable)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Python Build Tools
RUN pip install nuitka

WORKDIR /build
