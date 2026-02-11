#!/bin/bash
# Setup and Quick Start Script for DigitalOcean Serverless Deployment

set -e

echo "=================================="
echo "YouTube Stream URL - Quick Setup"
echo "=================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python
echo -e "${YELLOW}[1/5]${NC} Checking Python 3.11..."
if ! command -v python3.11 &> /dev/null; then
    echo -e "${RED}❌ Python 3.11 not found${NC}"
    echo "Please install Python 3.11"
    exit 1
fi
PYTHON_VERSION=$(python3.11 --version)
echo -e "${GREEN}✅ Found ${PYTHON_VERSION}${NC}"

# Create virtual environment
echo ""
echo -e "${YELLOW}[2/5]${NC} Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3.11 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null

# Install dependencies
echo ""
echo -e "${YELLOW}[3/5]${NC} Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r serverless_requirements.txt > /dev/null 2>&1
pip install pytest pytest-cov flake8 > /dev/null 2>&1
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Run tests
echo ""
echo -e "${YELLOW}[4/5]${NC} Running basic tests..."
if python test_serverless_local.py; then
    echo -e "${GREEN}✅ All tests passed${NC}"
else
    echo -e "${RED}❌ Tests failed${NC}"
    exit 1
fi

# Check doctl
echo ""
echo -e "${YELLOW}[5/5]${NC} Checking DigitalOcean CLI (doctl)..."
if command -v doctl &> /dev/null; then
    DOCTL_VERSION=$(doctl version)
    echo -e "${GREEN}✅ Found doctl: ${DOCTL_VERSION}${NC}"
else
    echo -e "${YELLOW}⚠️  doctl not found but optional for local development${NC}"
    echo "To install: https://docs.digitalocean.com/reference/doctl/how-to/install/"
fi

echo ""
echo "=================================="
echo -e "${GREEN}✨ Setup Complete!${NC}"
echo "=================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start the local development server:"
echo -e "   ${YELLOW}python serverless_handler.py${NC}"
echo ""
echo "2. In another terminal, test the endpoints:"
echo -e "   ${YELLOW}curl http://localhost:8000/health${NC}"
echo ""
echo "3. Open the Playground UI:"
echo -e "   ${YELLOW}http://localhost:8000/playground${NC}"
echo ""
echo "4. For deployment, read:"
echo -e "   ${YELLOW}cat DIGITALOCEAN_DEPLOYMENT.md${NC}"
echo ""
echo "5. Or follow the advanced plan:"
echo -e "   ${YELLOW}cat ADVANCED_IMPLEMENTATION_PLAN.md${NC}"
echo ""
