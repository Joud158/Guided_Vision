#!/bin/bash

# Docker management script for LLM Camera Tracker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if Docker is running
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not available. Please update Docker to a newer version."
        exit 1
    fi
}

# Function to check system requirements
check_requirements() {
    print_info "Checking system requirements..."
    
    # Check available memory
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        total_ram=$(sysctl -n hw.memsize)
        total_ram_gb=$((total_ram / 1024 / 1024 / 1024))
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        total_ram_gb=$(free -g | awk '/^Mem:/{print $2}')
    else
        print_warning "Cannot detect RAM on this system. Ensure you have at least 6GB RAM."
        total_ram_gb=6
    fi
    
    if [ "$total_ram_gb" -lt 2 ]; then
        print_warning "Only ${total_ram_gb}GB RAM detected. Minimum: 2GB required for SmolVLM-500M."
    else
        print_success "RAM check passed: ${total_ram_gb}GB available"
    fi
    
    # Check available disk space
    available_space=$(df . | awk 'NR==2{print $4}')
    available_gb=$((available_space / 1024 / 1024))
    
    if [ "$available_gb" -lt 5 ]; then
        print_warning "Only ${available_gb}GB disk space available. Recommended: 5GB+ for model storage."
    else
        print_success "Disk space check passed: ${available_gb}GB available"
    fi
}

# Function to download model files locally
ensure_model_downloaded() {
    local model_dir="./models"
    local model_file="$model_dir/SmolVLM-500M-Instruct-Q8_0.gguf"
    local mmproj_file="$model_dir/mmproj-SmolVLM-500M-Instruct-f16.gguf"
    local model_url="https://huggingface.co/ggml-org/SmolVLM-500M-Instruct-GGUF/resolve/main/SmolVLM-500M-Instruct-Q8_0.gguf"
    local mmproj_url="https://huggingface.co/ggml-org/SmolVLM-500M-Instruct-GGUF/resolve/main/mmproj-SmolVLM-500M-Instruct-f16.gguf"
    
    print_info "Checking for local model files..."
    
    # Create models directory
    mkdir -p "$model_dir"
    
    local model_complete=false
    local mmproj_complete=false
    
    # Check main model file
    if [ -f "$model_file" ]; then
        local file_size=$(stat -f%z "$model_file" 2>/dev/null || stat -c%s "$model_file" 2>/dev/null || echo "0")
        local expected_size=458319168  # 437MB in bytes for Q8_0 model
        
        if [ "$file_size" -ge "$expected_size" ]; then
            print_success "✅ Main model file ready"
            model_complete=true
        else
            print_warning "⚠️  Partial main model file found (${file_size} bytes), will resume download..."
        fi
    fi
    
    # Check mmproj file
    if [ -f "$mmproj_file" ]; then
        local mmproj_size=$(stat -f%z "$mmproj_file" 2>/dev/null || stat -c%s "$mmproj_file" 2>/dev/null || echo "0")
        local expected_mmproj_size=208666624  # 199MB in bytes for mmproj file
        
        if [ "$mmproj_size" -ge "$expected_mmproj_size" ]; then
            print_success "✅ MMProj file ready"
            mmproj_complete=true
        else
            print_warning "⚠️  Partial mmproj file found (${mmproj_size} bytes), will resume download..."
        fi
    fi
    
    # If both files are complete, we're done
    if [ "$model_complete" = true ] && [ "$mmproj_complete" = true ]; then
        print_success "🎉 All model files ready - instant startup!"
        return 0
    fi
    
    print_warning "📥 Downloading SmolVLM-500M files (~636MB total)..."
    print_info "This includes:"
    print_info "  • Main model: ~437MB"
    print_info "  • MMProj (vision): ~199MB"
    print_info "Download time: 2-15 minutes depending on your internet speed"
    print_info "Files will be saved locally for instant future startups!"
    
    # Download main model if needed
    if [ "$model_complete" != true ]; then
        print_info "📥 Downloading main model file..."
        if command -v curl >/dev/null 2>&1; then
            curl -L --progress-bar -C - -o "$model_file" --connect-timeout 30 --max-time 1800 "$model_url"
        elif command -v wget >/dev/null 2>&1; then
            wget --progress=bar:force:noscroll -c -O "$model_file" --timeout=30 "$model_url"
        else
            print_error "Neither wget nor curl found. Please install one of them."
            exit 1
        fi
        
        if [ $? -ne 0 ] || [ ! -f "$model_file" ]; then
            print_error "Failed to download main model file."
            rm -f "$model_file" 2>/dev/null
            exit 1
        fi
        print_success "✅ Main model downloaded"
    fi
    
    # Download mmproj file if needed
    if [ "$mmproj_complete" != true ]; then
        print_info "📥 Downloading MMProj (vision) file..."
        if command -v curl >/dev/null 2>&1; then
            curl -L --progress-bar -C - -o "$mmproj_file" --connect-timeout 30 --max-time 1800 "$mmproj_url"
        elif command -v wget >/dev/null 2>&1; then
            wget --progress=bar:force:noscroll -c -O "$mmproj_file" --timeout=30 "$mmproj_url"
        else
            print_error "Neither wget nor curl found. Please install one of them."
            exit 1
        fi
        
        if [ $? -ne 0 ] || [ ! -f "$mmproj_file" ]; then
            print_error "Failed to download mmproj file."
            rm -f "$mmproj_file" 2>/dev/null
            exit 1
        fi
        print_success "✅ MMProj file downloaded"
    fi
    
    print_success "🎉 All SmolVLM files downloaded successfully!"
}

# Function to start services
start_services() {
    print_info "Starting LLM Camera Tracker with SmolVLM-500M..."
    
    check_docker
    check_requirements
    
    # Ensure model is downloaded before starting Docker services
    ensure_model_downloaded
    
    print_info "Building and starting Docker containers..."
    print_success "Using cached model - fast startup!"
    
    docker compose up --build -d
    
    print_success "Services started!"
    print_info "Waiting for services to be ready..."
    
    # Wait for services to be healthy
    timeout=300  # 5 minutes
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if docker compose ps | grep -q "healthy"; then
            break
        fi
        sleep 10
        elapsed=$((elapsed + 10))
        print_info "Still waiting for services... (${elapsed}s/${timeout}s)"
    done
    
    if [ $elapsed -ge $timeout ]; then
        print_error "Services did not start within timeout. Check logs with: $0 logs"
        exit 1
    fi
    
    print_success "All services are ready!"
    print_info "🌍 Open your browser to: http://localhost:8000"
    print_info "📊 Scene Graph API: http://localhost:8081"
    print_info "🤖 LLM API: http://localhost:8080"
    print_info ""
    print_info "💡 To verify everything is working:"
    print_info "   curl http://localhost:8080/v1/models"
    print_info ""
    print_info "Run '$0 test' to verify everything is working"
    print_info "Run '$0 logs' to view service logs"
    print_info "Run '$0 stop' to stop all services"
}

# Function to stop services
stop_services() {
    print_info "Stopping LLM Camera Tracker..."
    docker compose down
    print_success "Services stopped!"
}

# Function to show logs
show_logs() {
    service=$2
    if [ -n "$service" ]; then
        print_info "Showing logs for service: $service"
        docker compose logs -f "$service"
    else
        print_info "Showing logs for all services (use Ctrl+C to exit)"
        docker compose logs -f
    fi
}

# Function to show status
show_status() {
    print_info "Service status:"
    docker compose ps
    
    print_info ""
    print_info "Container resource usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" || true
}

# Function to run tests
run_tests() {
    print_info "Running Docker setup tests..."
    if [ -f "test_docker_setup.py" ]; then
        python3 test_docker_setup.py
    else
        print_error "test_docker_setup.py not found. Please ensure you're in the project directory."
        exit 1
    fi
}

# Function to restart services
restart_services() {
    print_info "Restarting services..."
    docker compose restart
    print_success "Services restarted!"
}

# Function to clean up everything
cleanup() {
    print_warning "This will remove all containers, volumes, and cached data!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cleaning up Docker resources..."
        docker compose down -v
        docker compose rm -f
        docker system prune -f
        print_success "Cleanup completed!"
    else
        print_info "Cleanup cancelled."
    fi
}

# Function to show help
show_help() {
    echo "LLM Camera Tracker - Docker Management Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     Start all services with SmolVLM-500M"
    echo "  stop      Stop all services"
    echo "  restart   Restart all services"
    echo "  status    Show service status and resource usage"
    echo "  logs      Show logs for all services"
    echo "  logs SERVICE  Show logs for specific service"
    echo "  test      Run setup verification tests"
    echo "  cleanup   Remove all containers and volumes"
    echo "  help      Show this help message"
    echo ""
    echo "Services:"
    echo "  web-server         Frontend (port 8000)"
    echo "  scene-graph-server Backend API (port 8081)"
    echo "  llama-server       LLM API with SmolVLM-500M (port 8080)"
    echo ""
    echo "Examples:"
    echo "  $0                      # Start all services"
    echo "  $0 start                # Start all services (explicit)"
    echo "  $0 logs llama-server    # Show LLM server logs"
    echo "  $0 test                 # Test the setup"
    echo ""
    echo "Model Information:"
    echo "  SmolVLM-500M: ~636MB download (model + vision), 2GB RAM required"
    echo "  Includes: Main model (~437MB) + MMProj vision (~199MB)"
    echo "  First run: Files download automatically before Docker starts"
    echo "  Subsequent runs: Instant startup with cached files"
    echo ""
    echo "Features:"
    echo "  ✅ Complete vision model - handles images and text"
    echo "  ✅ Automatic file caching - no re-downloads"
    echo "  ✅ No Docker timeout issues - downloads happen outside containers"
    echo "  ✅ Resumable downloads if interrupted"
}

# Main script logic
case "$1" in
    "start"|"")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        restart_services
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs "$@"
        ;;
    "test")
        run_tests
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac 