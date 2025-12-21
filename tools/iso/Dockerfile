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
    ubuntu-keyring \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY build_iso.sh /usr/local/bin/build_iso.sh
RUN chmod +x /usr/local/bin/build_iso.sh

ENTRYPOINT ["/usr/local/bin/build_iso.sh"]
