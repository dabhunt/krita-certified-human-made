#!/bin/bash
#
# CI/CD Integration Script for Tamper Resistance Tests
#
# This script is designed for CI/CD environments (GitHub Actions, etc.)
# It runs the test suite and generates appropriate exit codes and reports.
#
# Usage:
#   ./tests/ci-tamper-tests.sh [--xml] [--coverage]
#
# Options:
#   --xml       Generate JUnit XML report for CI systems
#   --coverage  Generate code coverage report
#

set -e  # Exit on error

# Colors for output (disabled in CI)
if [ -t 1 ]; then
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    GREEN=''
    RED=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Parse arguments
GENERATE_XML=false
GENERATE_COVERAGE=false

for arg in "$@"; do
    case $arg in
        --xml)
            GENERATE_XML=true
            shift
            ;;
        --coverage)
            GENERATE_COVERAGE=true
            shift
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}CHM Tamper Resistance CI Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check Python version
echo -e "${YELLOW}[1/5] Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
echo "      Python ${PYTHON_VERSION}"

# Check for required Python version (3.7+)
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,7) else 1)"; then
    echo -e "${RED}      ✗ Python 3.7+ required${NC}"
    exit 1
fi
echo ""

# Check dependencies
echo -e "${YELLOW}[2/5] Checking dependencies...${NC}"

if [ "$GENERATE_XML" = true ]; then
    if ! python3 -c "import xmlrunner" 2>/dev/null; then
        echo "      Installing unittest-xml-reporting..."
        pip3 install unittest-xml-reporting --quiet
    fi
    echo "      ✓ unittest-xml-reporting available"
fi

if [ "$GENERATE_COVERAGE" = true ]; then
    if ! python3 -c "import coverage" 2>/dev/null; then
        echo "      Installing coverage..."
        pip3 install coverage --quiet
    fi
    echo "      ✓ coverage available"
fi
echo ""

# Check plugin directory
echo -e "${YELLOW}[3/5] Checking plugin directory...${NC}"
PLUGIN_DIR="${PROJECT_ROOT}/krita-plugin/chm_verifier"
if [ ! -d "$PLUGIN_DIR" ]; then
    echo -e "${RED}      ✗ Plugin directory not found: ${PLUGIN_DIR}${NC}"
    exit 1
fi
if [ ! -f "${PLUGIN_DIR}/chm_core.py" ]; then
    echo -e "${RED}      ✗ chm_core.py not found${NC}"
    exit 1
fi
echo "      ✓ Plugin directory OK"
echo ""

# Run tests
echo -e "${YELLOW}[4/5] Running test suite...${NC}"
echo ""

cd "$PROJECT_ROOT"

# Determine test command
TEST_CMD="python3 ${SCRIPT_DIR}/test_tamper_resistance.py"

if [ "$GENERATE_COVERAGE" = true ]; then
    echo "      Running with coverage..."
    coverage run --source=krita-plugin/chm_verifier "${SCRIPT_DIR}/test_tamper_resistance.py"
    TEST_EXIT_CODE=$?
else
    $TEST_CMD
    TEST_EXIT_CODE=$?
fi

echo ""

# Generate reports
echo -e "${YELLOW}[5/5] Generating reports...${NC}"

if [ "$GENERATE_COVERAGE" = true ]; then
    echo "      Generating coverage report..."
    coverage report -m
    coverage html -d tests/htmlcov
    echo "      ✓ Coverage report: tests/htmlcov/index.html"
fi

if [ "$GENERATE_XML" = true ]; then
    echo "      XML report generation requires unittest-xml-reporting"
    echo "      (TODO: Integrate with test suite)"
fi

echo ""

# Final result
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ TESTS FAILED${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi

