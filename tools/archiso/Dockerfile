FROM archlinux:base-devel

# Initialize Pacman keyring
RUN pacman-key --init && \
    pacman-key --populate archlinux

# Update and Install Dependencies
# - archiso: The build tool
# - git, wget: Fetching tools
# - python, python-pip: For Nuitka and Loop scripts
# - nodejs, npm: For GUI frontend
# - rust, cargo: For GUI backend (Tauri)
# - webkit2gtk, openssl: Tauri dependencies
# - squashfs-tools: For filesystem manipulation
RUN pacman -Syu --noconfirm && \
    pacman -S --noconfirm \
    archiso \
    git \
    wget \
    python \
    python-pip \
    nodejs \
    npm \
    rust \
    cargo \
    webkit2gtk \
    openssl \
    squashfs-tools \
    patchelf \
    python-greenlet

# Install pnpm via npm to ensure availability
RUN npm install -g pnpm

# Pre-install Nuitka
RUN pip install nuitka --break-system-packages

WORKDIR /repo
