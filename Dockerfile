# Stage 1: Builder
FROM python:3.10-slim AS builder

# 1. Install system dependencies
# 'build-essential' provides g++ (Required for C++ compilation)
# 'patchelf' is required by Nuitka for standalone linux builds
# 'git' is often needed by Nuitka/Pip for versioning
RUN apt-get update && apt-get install -y \
    build-essential \
    patchelf \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Copy the entire repository
COPY . .

# 3. Install dependencies AND build tools
# We install 'scons' explicitly as it powers Nuitka's build backend
# CRITICAL: Build tools installed FIRST to prevent setup_extensions.py failure
RUN pip install --no-cache-dir pybind11 nuitka scons && \
    pip install --no-cache-dir -r requirements.txt

# 4. CI/CD OPTIMIZATION: "Turbo Mode" 🚀
# NUITKA_PROGRESS_BAR=0: Disables the interactive UI (Prevents log buffering hangs)
# NUITKA_QUIET=0: Ensures errors are printed immediately
# PYTHONUNBUFFERED=1: Forces Python to flush stdout immediately
ENV NUITKA_PROGRESS_BAR=0
ENV NUITKA_QUIET=0
ENV PYTHONUNBUFFERED=1

# UNLEASH THE HARDWARE: Use all 4 Cores
ENV NUITKA_JOBS=4

# VISUAL FEEDBACK: Show the C compiler working (No more silent hangs!)
ENV NUITKA_SHOW_SCONS=1

# Step A: Compile C++ Extensions
RUN python setup_extensions.py build_ext --inplace

# Step B: Build the kernel (Nuitka)
# We use 'python -u' (unbuffered) as a second layer of defense
RUN python -u scripts/build_kernel.py

# Stage 2: Runtime
FROM python:3.10-slim AS runtime

# Create a non-root user
RUN useradd -m -s /bin/bash loop

WORKDIR /app

# Create the .loop directory structure with correct permissions
RUN mkdir -p /home/loop/.loop && \
    chown -R loop:loop /home/loop

# Copy the compiled binary
# We use the 'gui/' path here because Nuitka puts it there
COPY --from=builder --chown=loop:loop /app/gui/src-tauri/bin/loop-kernel /app/loop-kernel

# Switch to non-root user
USER loop

# Expose the default port
EXPOSE 8000

# Entrypoint configuration
ENTRYPOINT ["/app/loop-kernel", "serve", "--host", "0.0.0.0", "--port", "8000"]
