# Native Installation (Advanced Users)

This folder contains native installation methods for advanced users who need custom environments or want to develop/debug the core components.

**⚠️ Note: Docker is the recommended installation method. Use native installation only if you have specific requirements that Docker cannot fulfill.**

## Files

### `MANUAL_INSTALL.md`
Comprehensive step-by-step instructions for manual installation, including:
- Cross-platform installation steps (Windows, macOS, Linux)
- Dependency management and troubleshooting
- Custom environment configuration
- Development setup instructions

### `test_installation.py` 
Validation script to verify all native dependencies are properly installed:
```bash
cd legacy/
python3 test_installation.py
```

## When to Use Native Installation

- **Development & Debugging**: Core component development and debugging
- **Custom Environments**: Environments where Docker is restricted or unavailable
- **Research**: Academic or research projects requiring native Python access
- **Integration**: Embedding into existing Python/web applications
- **Educational**: Understanding the complete dependency chain and system architecture
- **Performance**: Maximum performance without Docker overhead

## System Requirements

### Minimum Requirements
- **Python**: 3.8+ with pip and venv
- **RAM**: 4GB minimum (varies by model selection)
- **Storage**: 5GB+ available space
- **Network**: Internet connection for initial setup

### Platform-Specific Requirements

**macOS:**
- Homebrew package manager
- Xcode Command Line Tools
- Metal support (recommended for performance)

**Linux:**
- Build tools: `gcc`, `cmake`, `make`
- Development libraries: `libcurl4-openssl-dev`, `pkg-config`
- Package manager: `apt`, `yum`, or equivalent

**Windows:**
- Visual Studio Build Tools or equivalent
- Windows Subsystem for Linux (WSL) recommended
- Git for Windows

## Installation Process

1. **Follow Manual Guide**: Complete step-by-step instructions in `MANUAL_INSTALL.md`
2. **Validate Setup**: Run `python3 test_installation.py` to verify installation
3. **Start Services**: Follow the manual startup procedures in the guide

## Model Selection

The native installation supports the same three models as Docker:
- **SmolVLM-500M**: Lightweight, good for development
- **LLaVA-1.5-7B**: Balanced performance (requires HF token)
- **LLaVA-Llama-3-8B**: Highest quality (requires HF token)

Refer to the main README for detailed model specifications and requirements.

## Support & Troubleshooting

**Primary Support**: Docker installation (see main README)

**Legacy Support**: 
1. Check troubleshooting in `MANUAL_INSTALL.md`
2. Verify system requirements are met
3. Consider migrating to Docker for better support

## Migration to Docker

To switch from native to Docker installation:

1. Stop all running native services
2. Return to the main project directory: `cd ..`
3. Follow the Docker quick start: `./run_docker.sh start small`
4. All your previous work and configurations will be preserved
4. Your models and data will be preserved in Docker volumes 