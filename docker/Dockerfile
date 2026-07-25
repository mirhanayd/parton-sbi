# Use a specific, pinned Ubuntu version
FROM ubuntu:22.04

# Avoid tzdata interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Update system and install all necessary system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    curl \
    git \
    wget \
    pkg-config \
    libssl-dev \
    libfontconfig1-dev \
    libfontconfig1 \
    libxcb-shape0-dev \
    libxcb-xfixes0-dev \
    libxkbcommon-dev \
    python3 \
    python3-pip \
    python3-venv \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain (pinned to 1.76.0 or latest stable, here we use stable but you can pin)
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:$PATH

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable

# Create a non-root user for building
RUN useradd -ms /bin/bash quark && echo "quark:quark" | chpasswd && adduser quark sudo
USER quark
WORKDIR /home/quark/quark_sim

# Create Python virtual environment
RUN python3 -m venv /home/quark/quark_sim/.venv
ENV PATH="/home/quark/quark_sim/.venv/bin:$PATH"

# Install Python requirements
COPY --chown=quark:quark analysis/requirements.txt analysis/
RUN pip install --no-cache-dir -r analysis/requirements.txt

# Copy scripts and install external physics dependencies
COPY --chown=quark:quark scripts/ scripts/
RUN ./scripts/setup_all_wsl.sh

# Copy the rest of the application
COPY --chown=quark:quark . .

# Build the Rust application (using the apfelxx_env.sh variables)
RUN bash -l -c "source scripts/apfelxx_env.sh && cargo build --release"

# Default entrypoint activates the environment
ENTRYPOINT ["bash", "-l", "-c", "source scripts/apfelxx_env.sh && exec \"$@\"", "--"]
CMD ["cargo", "run", "--release", "--", "--help"]
