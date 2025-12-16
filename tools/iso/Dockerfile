FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    live-build \
    debootstrap \
    squashfs-tools \
    xorriso \
    isolinux \
    syslinux-common \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY build_iso.sh /usr/local/bin/build_iso.sh
RUN chmod +x /usr/local/bin/build_iso.sh

ENTRYPOINT ["/usr/local/bin/build_iso.sh"]
