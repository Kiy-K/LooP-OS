FROM ubuntu:jammy

ENV DEBIAN_FRONTEND=noninteractive

# Last Updated: 2025-05-24 (Cache Buster)
# Install build dependencies
# We switched to Ubuntu base to ensure ubuntu-keyring is present natively
RUN apt-get update && apt-get install -y \
    live-build \
    debootstrap \
    squashfs-tools \
    xorriso \
    isolinux \
    syslinux-common \
    syslinux-utils \
    grub-pc-bin \
    grub-efi-amd64-bin \
    mtools \
    dosfstools \
    git \
    curl \
    wget \
    gnupg \
    file \
    build-essential \
    libssl-dev \
    libgtk-3-dev \
    libayatana-appindicator3-dev \
    librsvg2-dev \
    libwebkit2gtk-4.0-dev \
    ubuntu-keyring \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 18
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g pnpm

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /build

COPY build_iso.sh /usr/local/bin/build_iso.sh
RUN chmod +x /usr/local/bin/build_iso.sh

ENTRYPOINT ["/usr/local/bin/build_iso.sh"]
