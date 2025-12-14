# Stage 1: Builder
FROM python:3.10-slim AS builder

# Install system dependencies for Nuitka compilation
# gcc: for compilation
# ccache: to speed up recompilation (optional but good practice)
# patchelf: required by Nuitka for standalone linux builds
RUN apt-get update && apt-get install -y \
    gcc \
    ccache \
    patchelf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the entire repository
COPY . .

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir pybind11 nuitka

# Step A: Compile C++ Extensions
RUN python setup_extensions.py build_ext --inplace

# Step B: Build the kernel (Nuitka)
# The script outputs to gui/src-tauri/bin/fyodor-kernel
RUN python scripts/build_kernel.py

# Stage 2: Runtime
FROM python:3.10-slim AS runtime

# Create a non-root user
RUN useradd -m -s /bin/bash fyodor

WORKDIR /app

# Create the .fyodor directory structure with correct permissions
RUN mkdir -p /home/fyodor/.fyodor && \
    chown -R fyodor:fyodor /home/fyodor

# Copy the compiled binary from the builder stage with correct ownership
COPY --from=builder --chown=fyodor:fyodor /app/gui/src-tauri/bin/fyodor-kernel /app/fyodor-kernel

# Switch to non-root user
USER fyodor

# Expose the default port (optional documentation)
EXPOSE 8000

# Entrypoint configuration
# Serve on all interfaces (0.0.0.0) so Docker networking works
ENTRYPOINT ["/app/fyodor-kernel", "serve", "--host", "0.0.0.0", "--port", "8000"]
