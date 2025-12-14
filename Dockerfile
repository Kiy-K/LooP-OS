# Stage 1: Builder
FROM python:3.10-slim AS builder

# Install system dependencies for Nuitka compilation
RUN apt-get update && apt-get install -y \
    gcc \
    ccache \
    patchelf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the entire repository
COPY . .

# Install dependencies AND build tools explicitely
# We chain commands to ensure pybind11 exists before the next step runs
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pybind11 nuitka

# Step A: Compile C++ Extensions (This failed before because pybind11 was missing)
RUN python setup_extensions.py build_ext --inplace

# Step B: Build the kernel (Nuitka)
# This outputs to /app/src-tauri/bin/fyodor-kernel
RUN python scripts/build_kernel.py

# Stage 2: Runtime
FROM python:3.10-slim AS runtime

# Create a non-root user for security
RUN useradd -m -s /bin/bash fyodor

WORKDIR /app

# Create the .fyodor config directory with correct permissions
RUN mkdir -p /home/fyodor/.fyodor && \
    chown -R fyodor:fyodor /home/fyodor

# Copy the compiled binary
# Note: Ensure scripts/build_kernel.py actually outputs to src-tauri/bin
COPY --from=builder --chown=fyodor:fyodor /app/src-tauri/bin/fyodor-kernel /app/fyodor-kernel

# Switch to non-root user
USER fyodor

# Expose port
EXPOSE 8000

# Entrypoint configuration
ENTRYPOINT ["/app/fyodor-kernel", "serve", "--host", "0.0.0.0", "--port", "8000"]
