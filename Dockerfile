# Base Python image
FROM python:3.11-slim

# Set workdir inside container
WORKDIR /app

# Install system dependencies (needed for Pillow / OpenCV / etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy server dependencies file and install
COPY requirements_server.txt ./requirements_server.txt

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements_server.txt

# Copy only the server code into the container
COPY server/ ./server

# Work inside the server directory (where main.py lives)
WORKDIR /app/server

# Expose FastAPI port
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"]
