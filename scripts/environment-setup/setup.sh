#!/bin/bash
set -e

echo "=========================================="
echo "  RolloForge Environment Setup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Detect OS
OS=""
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    OS="unknown"
fi

print_status "Detected OS: $OS"

# Check Python version
echo ""
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_status "Python version: $PYTHON_VERSION"
    
    # Check if Python version is 3.10 or higher
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
        print_error "Python 3.10 or higher is required"
        exit 1
    fi
else
    print_error "Python 3 is not installed. Please install Python 3.10 or higher."
    exit 1
fi

# Check Node.js version (for dashboard)
echo ""
echo "Checking Node.js version..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | cut -d'v' -f2)
    print_status "Node.js version: $NODE_VERSION"
else
    print_warning "Node.js not found. Dashboard development will require Node.js 20.x"
    print_warning "Install from: https://nodejs.org/"
fi

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
if [ -d ".venv" ]; then
    print_warning ".venv already exists. Removing old environment..."
    rm -rf .venv
fi

python3 -m venv .venv
print_status "Virtual environment created"

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source .venv/bin/activate
print_status "Virtual environment activated"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel
print_status "pip upgraded"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt -r requirements-security.txt
print_status "Python dependencies installed"

# Install Playwright
echo ""
echo "Installing Playwright..."
pip install playwright
print_status "Playwright installed"

# Install Playwright browsers
echo ""
echo "Installing Playwright Chromium browser (this may take a few minutes)..."
playwright install chromium
print_status "Chromium browser installed"

# Create .env file if it doesn't exist
echo ""
echo "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_status ".env file created from .env.example"
        print_warning "⚠ Please edit .env and add your DEEPSEEK_API_KEY"
    else
        touch .env
        print_warning ".env.example not found. Created empty .env file"
    fi
else
    print_warning ".env file already exists (not overwritten)"
fi

# Create necessary directories
echo ""
echo "Creating necessary directories..."
mkdir -p data logs reports
print_status "Directories created"

# Setup git hooks (optional)
echo ""
echo "Setting up git hooks..."
if [ -d ".githooks" ]; then
    git config core.hooksPath .githooks
    print_status "Git hooks configured"
else
    print_warning "No .githooks directory found, skipping"
fi

# Run health check
echo ""
echo "Running health check..."
if python -c "import rolloforge.deepseek_analysis; print('OK')" 2>/dev/null; then
    print_status "Health check passed"
else
    print_warning "Health check could not verify imports (may need .env configuration)"
fi

# Summary
echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
print_status "RolloForge development environment is ready!"
echo ""
echo "Next steps:"
echo ""
echo "  1. Configure your API keys:"
echo "     Edit .env and add your DEEPSEEK_API_KEY"
echo ""
echo "  2. Activate the virtual environment:"
echo "     source .venv/bin/activate"
echo ""
echo "  3. Test the CLI:"
echo "     ./forge stats"
echo ""
echo "  4. Start the dashboard (requires Node.js):"
echo "     cd web && npm install && npm run dev"
echo ""
echo "  5. Or use Docker for full stack:"
echo "     docker-compose -f scripts/environment-setup/docker-compose.yml up -d"
echo ""
