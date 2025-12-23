FROM ubuntu:jammy

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    squashfs-tools \
    xorriso \
    p7zip-full \
    wget \
    curl \
    git \
    rsync \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY . /build

ENTRYPOINT ["/bin/bash", "tools/remaster/build_loop_distro.sh"]
