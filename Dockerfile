# Multi-stage build for LLM Camera Tracker
FROM ubuntu:22.04 as llama-builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    libcurl4-openssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Build llama.cpp from source
WORKDIR /tmp
RUN git clone https://github.com/ggerganov/llama.cpp.git
WORKDIR /tmp/llama.cpp
RUN mkdir build && cd build && \
    cmake .. -DGGML_BACKEND_DL=OFF -DLLAMA_SERVER=ON -DBUILD_SHARED_LIBS=OFF -DGGML_STATIC=ON && \
    cmake --build . --config Release --target llama-server

# Main application stage
FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    libgomp1 \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# Copy llama-server binary from builder stage
COPY --from=llama-builder /tmp/llama.cpp/build/bin/llama-server /usr/local/bin/llama-server
RUN chmod +x /usr/local/bin/llama-server

# Create app user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy Python requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install Python dependencies
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install "urllib3<2.0.0" && \
    pip install numpy==1.24.3 && \
    pip install thinc==8.1.12 && \
    pip install spacy==3.5.3 && \
    pip install -r requirements.txt

# Download spaCy language model
RUN python3 -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Create output directory
RUN mkdir -p output

# Change ownership to app user
RUN chown -R appuser:appuser /app /opt/venv

# Switch to app user
USER appuser

# Expose ports
EXPOSE 8000 8080 8081

# Health check script
COPY --chown=appuser:appuser docker-healthcheck.sh /app/
RUN chmod +x /app/docker-healthcheck.sh

# Default command (overridden by docker-compose)
CMD ["python3", "scene_graph_server.py"] 