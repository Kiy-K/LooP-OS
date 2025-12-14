# Stage 1: Builder
FROM python:3.10-slim AS builder

# Install system dependencies for Nuitka compilation
# CRITICAL: 'build-essential' provides g++ (needed for your C++ extensions)
# 'patchelf' is required by Nuitka for standalone linux builds
RUN apt-get update && apt-get install -y \
    build-essential \
    ccache \
    patchelf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the entire repository
COPY . .

# Install dependencies AND build tools (pybind11 + Nuitka)
# CRITICAL: Install build tools FIRST to prime environment for extensions
RUN pip install --no-cache-dir pybind11 nuitka && \
    pip install --no-cache-dir -r requirements.txt

# Step A: Compile C++ Extensions
RUN python setup_extensions.py build_ext --inplace

# Step B: Build the kernel (Nuitka)
# This outputs to /app/gui/src-tauri/bin/fyodor-kernel
RUN python scripts/build_kernel.py

# Stage 2: Runtime
FROM python:3.10-slim AS runtime

# Create a non-root user
RUN useradd -m -s /bin/bash fyodor

WORKDIR /app

# Create the .fyodor directory structure with correct permissions
RUN mkdir -p /home/fyodor/.fyodor && \
    chown -R fyodor:fyodor /home/fyodor

# Copy the compiled binary
# We use the 'gui/' path here because Nuitka puts it there
COPY --from=builder --chown=fyodor:fyodor /app/gui/src-tauri/bin/fyodor-kernel /app/fyodor-kernel

# Switch to non-root user
USER fyodor

# Expose the default port
EXPOSE 8000

# Entrypoint configuration
ENTRYPOINT ["/app/fyodor-kernel", "serve", "--host", "0.0.0.0", "--port", "8000"]
