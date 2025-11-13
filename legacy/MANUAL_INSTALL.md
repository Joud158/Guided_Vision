# Manual Installation Guide

> **Note:** This manual installation guide is the **preferred route for Windows users**, since the automated setup script (`run_demo.sh`) is designed for macOS and Linux systems.

This guide provides step-by-step instructions for manually setting up the LLM Camera Tracker project without using the automated script. This is useful for users who want more control over the installation process or are working in environments where the shell script cannot be used.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- At least 4GB of RAM
- Git (optional, for cloning the repository)

## Step 1: Clone the Repository (Optional)

If you haven't already downloaded the project:

```bash
git clone https://github.com/AmmarMohanna/llm-camera-tracker.git
cd llm-camera-tracker
```

## Step 2: Create and Activate Virtual Environment

```bash
# Create a new virtual environment
python3 -m venv realtime_llm

# Activate the virtual environment
# On macOS/Linux:
source realtime_llm/bin/activate
# On Windows:
# .\realtime_llm\Scripts\activate
```

## Step 3: Install Dependencies

```bash
# Upgrade pip
python3 -m pip install --upgrade pip setuptools wheel

# Clean up any existing installations
python3 -m pip uninstall -y numpy spacy thinc urllib3 requests

# Install specific versions for compatibility
python3 -m pip install urllib3<2.0.0  # Fix SSL compatibility
python3 -m pip install numpy==1.24.3
python3 -m pip install thinc==8.1.12
python3 -m pip install spacy==3.5.3

# Install the rest of the requirements
python3 -m pip install -r requirements.txt

# Install spaCy language model
python3 -m spacy download en_core_web_sm
```

If you still encounter any issues, try this alternative approach:

```bash
# Create a fresh virtual environment
deactivate
rm -rf realtime_llm
python3 -m venv realtime_llm
source realtime_llm/bin/activate

# Install dependencies in specific order
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install urllib3<2.0.0  # Fix SSL compatibility
python3 -m pip install numpy==1.24.3
python3 -m pip install thinc==8.1.12
python3 -m pip install spacy==3.5.3
python3 -m spacy download en_core_web_sm
python3 -m pip install -r requirements.txt
```

## Step 4: Install llama.cpp

### On macOS (Recommended)

Install llama.cpp using Homebrew:

```bash
brew install llama.cpp
```

This will provide the `llama-server` binary in your PATH.

### On Linux

Follow the official instructions to build llama.cpp from source:

```bash
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
make
sudo cp ./server /usr/local/bin/llama-server
```

This will provide the `llama-server` binary in your PATH.

> **Note:** You do **NOT** need to install `llama-cpp-python` in your Python environment. The server runs as a standalone process.

## Step 5: Create Output Directory

```bash
# Create directory for graph outputs
mkdir -p output
```

## Step 6: Start the Services

You'll need to start three services in separate terminal windows:

1. **Start llama-server** (Terminal 1):
```bash
llama-server -hf ggml-org/SmolVLM-500M-Instruct-GGUF
```

2. **Start scene graph server** (Terminal 2):
```bash
python3 scene_graph_server.py
```

3. **Start HTTP server** (Terminal 3):
```bash
python3 -m http.server 8000
```

## Step 7: Access the Web Interface

Open your web browser and navigate to:
```
http://localhost:8000/index.html
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   - If you see "Address already in use" errors, make sure no other services are using ports 8000, 8080, or 8081
   - You can check port usage with:
     ```bash
     # On macOS/Linux:
     lsof -i :8000
     lsof -i :8080
     lsof -i :8081
     ```

2. **Model Download Issues**
   - The model will be downloaded automatically on first run
   - If download fails, check your internet connection
   - The model is approximately 500MB in size

3. **Python Package Issues**
   - If you encounter package conflicts, try:
     ```bash
     python3 -m pip install --upgrade --force-reinstall -r requirements.txt
     ```

4. **Memory Issues**
   - If you see out-of-memory errors, ensure you have at least 4GB of free RAM
   - Close other memory-intensive applications

### Logs

Check these log files for detailed error information:
- `llama-server.log`
- `scene-graph-server.log`
- `http-server.log`

## Stopping the Services

To stop all services:
1. Press Ctrl+C in each terminal window
2. Deactivate the virtual environment:
   ```bash
   deactivate
   ```

## Next Steps

After installation, you can:
1. Start capturing and analyzing video
2. Export graph data
3. Use the visualization tools

For more information, refer to the main [README.md](README.md) file. 