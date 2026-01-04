#!/bin/bash
#
# Run Tamper Resistance Test Suite
#
# This script runs the automated tamper resistance tests.
# It handles environment setup and provides clear output.
#
# Usage:
#   ./tests/run-tamper-tests.sh           # Run all tests
#   ./tests/run-tamper-tests.sh --verbose # Run with verbose output
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}CHM Tamper Resistance Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check Python version
echo -e "${YELLOW}[1/4] Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
echo "      ✓ Python ${PYTHON_VERSION}"
echo ""

# Check plugin directory
echo -e "${YELLOW}[2/4] Checking plugin directory...${NC}"
PLUGIN_DIR="${PROJECT_ROOT}/krita-plugin/chm_verifier"
if [ ! -d "$PLUGIN_DIR" ]; then
    echo -e "${RED}      ✗ Plugin directory not found: ${PLUGIN_DIR}${NC}"
    exit 1
fi
echo "      ✓ Plugin directory: ${PLUGIN_DIR}"
echo ""

# Check core module
echo -e "${YELLOW}[3/4] Checking chm_core module...${NC}"
if [ ! -f "${PLUGIN_DIR}/chm_core.py" ]; then
    echo -e "${RED}      ✗ chm_core.py not found${NC}"
    exit 1
fi
echo "      ✓ chm_core.py found"
echo ""

# Run tests
echo -e "${YELLOW}[4/4] Running test suite...${NC}"
echo ""

cd "$PROJECT_ROOT"

# Check for verbose flag
VERBOSE=""
if [ "$1" = "--verbose" ] || [ "$1" = "-v" ]; then
    VERBOSE="-v"
fi

# Run the test suite
if python3 "${SCRIPT_DIR}/test_tamper_resistance.py" $VERBOSE; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi

