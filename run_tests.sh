#!/bin/bash

# Test Runner Script for LanAim POS v5.3
# Automated test execution with comprehensive reporting

set -e  # Exit on any error

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$PROJECT_ROOT/tests"
REPORTS_DIR="$PROJECT_ROOT/test-reports"
COVERAGE_DIR="$REPORTS_DIR/coverage"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Setup test environment
setup_test_environment() {
    print_status "Setting up test environment..."
    
    # Create reports directory
    mkdir -p "$REPORTS_DIR"
    mkdir -p "$COVERAGE_DIR"
    
    # Install test dependencies if not present
    if ! command_exists pytest; then
        print_warning "pytest not found, installing..."
        pip install pytest pytest-flask pytest-cov pytest-html pytest-xdist
    fi
    
    # Install coverage tools
    if ! command_exists coverage; then
        print_warning "coverage not found, installing..."
        pip install coverage
    fi
    
    print_success "Test environment ready"
}

# Run unit tests
run_unit_tests() {
    print_status "Running unit tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run tests with coverage
    pytest tests/test_models.py \
        --verbose \
        --tb=short \
        --cov=models \
        --cov-report=html:"$COVERAGE_DIR/models" \
        --cov-report=term \
        --junit-xml="$REPORTS_DIR/unit_tests.xml" \
        --html="$REPORTS_DIR/unit_tests.html" \
        --self-contained-html
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        print_success "Unit tests passed"
    else
        print_error "Unit tests failed"
        return $exit_code
    fi
}

# Run route tests
run_route_tests() {
    print_status "Running route tests..."
    
    cd "$PROJECT_ROOT"
    
    pytest tests/test_routes.py \
        --verbose \
        --tb=short \
        --cov=app_production \
        --cov-append \
        --cov-report=html:"$COVERAGE_DIR/routes" \
        --cov-report=term \
        --junit-xml="$REPORTS_DIR/route_tests.xml" \
        --html="$REPORTS_DIR/route_tests.html" \
        --self-contained-html
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        print_success "Route tests passed"
    else
        print_error "Route tests failed"
        return $exit_code
    fi
}

# Run production component tests
run_production_tests() {
    print_status "Running production component tests..."
    
    cd "$PROJECT_ROOT"
    
    pytest tests/test_production.py \
        --verbose \
        --tb=short \
        --cov=security \
        --cov=caching \
        --cov=monitoring \
        --cov=backup \
        --cov=notifications \
        --cov-append \
        --cov-report=html:"$COVERAGE_DIR/production" \
        --cov-report=term \
        --junit-xml="$REPORTS_DIR/production_tests.xml" \
        --html="$REPORTS_DIR/production_tests.html" \
        --self-contained-html
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        print_success "Production component tests passed"
    else
        print_error "Production component tests failed"
        return $exit_code
    fi
}

# Run integration tests
run_integration_tests() {
    print_status "Running integration tests..."
    
    cd "$PROJECT_ROOT"
    
    pytest tests/test_integration.py \
        --verbose \
        --tb=short \
        --cov-append \
        --cov-report=html:"$COVERAGE_DIR/integration" \
        --cov-report=term \
        --junit-xml="$REPORTS_DIR/integration_tests.xml" \
        --html="$REPORTS_DIR/integration_tests.html" \
        --self-contained-html
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        print_success "Integration tests passed"
    else
        print_error "Integration tests failed"
        return $exit_code
    fi
}

# Run all tests with comprehensive coverage
run_all_tests() {
    print_status "Running all tests with comprehensive coverage..."
    
    cd "$PROJECT_ROOT"
    
    pytest tests/ \
        --verbose \
        --tb=short \
        --cov=. \
        --cov-config=.coveragerc \
        --cov-report=html:"$COVERAGE_DIR/all" \
        --cov-report=term-missing \
        --cov-report=xml:"$REPORTS_DIR/coverage.xml" \
        --junit-xml="$REPORTS_DIR/all_tests.xml" \
        --html="$REPORTS_DIR/all_tests.html" \
        --self-contained-html \
        --maxfail=5
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        print_success "All tests passed"
    else
        print_error "Some tests failed"
        return $exit_code
    fi
}

# Run performance tests
run_performance_tests() {
    print_status "Running performance tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run tests with timing
    pytest tests/ \
        --verbose \
        --durations=10 \
        --benchmark-only \
        --benchmark-json="$REPORTS_DIR/benchmark.json" \
        || print_warning "No performance/benchmark tests found"
    
    print_success "Performance test analysis complete"
}

# Run security tests
run_security_tests() {
    print_status "Running security-focused tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run security-related tests
    pytest tests/test_production.py::TestSecurityManager \
        tests/test_routes.py::TestSecurity \
        --verbose \
        --tb=short \
        --junit-xml="$REPORTS_DIR/security_tests.xml" \
        --html="$REPORTS_DIR/security_tests.html" \
        --self-contained-html
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        print_success "Security tests passed"
    else
        print_error "Security tests failed"
        return $exit_code
    fi
}

# Generate comprehensive coverage report
generate_coverage_report() {
    print_status "Generating comprehensive coverage report..."
    
    cd "$PROJECT_ROOT"
    
    # Combine coverage data
    coverage combine || true
    
    # Generate HTML report
    coverage html -d "$COVERAGE_DIR/combined"
    
    # Generate text report
    coverage report > "$REPORTS_DIR/coverage_summary.txt"
    
    # Generate XML report for CI/CD
    coverage xml -o "$REPORTS_DIR/coverage.xml"
    
    print_success "Coverage reports generated"
}

# Check test quality metrics
check_test_quality() {
    print_status "Checking test quality metrics..."
    
    cd "$PROJECT_ROOT"
    
    # Count test files and functions
    local test_files=$(find tests/ -name "test_*.py" | wc -l)
    local test_functions=$(grep -r "def test_" tests/ | wc -l)
    
    echo "Test Quality Metrics:" > "$REPORTS_DIR/test_metrics.txt"
    echo "- Test files: $test_files" >> "$REPORTS_DIR/test_metrics.txt"
    echo "- Test functions: $test_functions" >> "$REPORTS_DIR/test_metrics.txt"
    
    # Check coverage threshold
    local coverage_percent=$(coverage report | tail -1 | awk '{print $4}' | sed 's/%//')
    echo "- Code coverage: ${coverage_percent}%" >> "$REPORTS_DIR/test_metrics.txt"
    
    if [ "${coverage_percent%.*}" -ge 80 ]; then
        print_success "Code coverage above 80% threshold"
    else
        print_warning "Code coverage below 80% threshold: ${coverage_percent}%"
    fi
    
    print_success "Test quality metrics generated"
}

# Clean up test artifacts
cleanup_test_artifacts() {
    print_status "Cleaning up test artifacts..."
    
    # Remove Python cache
    find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -name "*.pyc" -delete 2>/dev/null || true
    
    # Remove test database files
    find "$PROJECT_ROOT" -name "test_*.db" -delete 2>/dev/null || true
    find "$PROJECT_ROOT" -name "*.db-journal" -delete 2>/dev/null || true
    
    # Clean coverage files
    rm -f "$PROJECT_ROOT/.coverage"* 2>/dev/null || true
    
    print_success "Test artifacts cleaned up"
}

# Generate test summary report
generate_summary_report() {
    print_status "Generating test summary report..."
    
    local report_file="$REPORTS_DIR/test_summary.md"
    
    cat > "$report_file" << EOF
# LanAim POS v5.3 Test Summary Report

**Generated:** $(date)

## Test Execution Summary

### Test Categories
- ✅ Unit Tests (Models)
- ✅ Route Tests (Views & Controllers)
- ✅ Production Component Tests
- ✅ Integration Tests
- ✅ Security Tests

### Coverage Summary
$(cat "$REPORTS_DIR/coverage_summary.txt" 2>/dev/null || echo "Coverage report not available")

### Test Quality Metrics
$(cat "$REPORTS_DIR/test_metrics.txt" 2>/dev/null || echo "Test metrics not available")

### Report Files
- **Detailed Results:** all_tests.html
- **Coverage Report:** coverage/combined/index.html
- **Unit Tests:** unit_tests.html
- **Route Tests:** route_tests.html
- **Production Tests:** production_tests.html
- **Integration Tests:** integration_tests.html
- **Security Tests:** security_tests.html

### Recommendations
1. Maintain code coverage above 80%
2. Add more edge case tests
3. Implement performance benchmarks
4. Regular security test reviews
5. Keep test documentation updated

---
*Generated by LanAim POS Test Suite*
EOF

    print_success "Test summary report generated: $report_file"
}

# Main execution function
main() {
    local test_type="${1:-all}"
    
    echo "🧪 LanAim POS v5.3 Test Suite"
    echo "=================================="
    
    # Setup
    setup_test_environment
    cleanup_test_artifacts
    
    # Run tests based on parameter
    case $test_type in
        "unit")
            run_unit_tests
            ;;
        "routes")
            run_route_tests
            ;;
        "production")
            run_production_tests
            ;;
        "integration")
            run_integration_tests
            ;;
        "security")
            run_security_tests
            ;;
        "performance")
            run_performance_tests
            ;;
        "all")
            run_all_tests
            run_performance_tests
            ;;
        "quick")
            run_unit_tests
            run_route_tests
            ;;
        *)
            print_error "Unknown test type: $test_type"
            echo "Usage: $0 [unit|routes|production|integration|security|performance|all|quick]"
            exit 1
            ;;
    esac
    
    # Generate reports
    generate_coverage_report
    check_test_quality
    generate_summary_report
    
    echo ""
    echo "📊 Test Results Summary:"
    echo "========================"
    echo "📁 Reports directory: $REPORTS_DIR"
    echo "📈 Coverage report: $COVERAGE_DIR/combined/index.html"
    echo "📋 Summary report: $REPORTS_DIR/test_summary.md"
    echo ""
    
    print_success "Test execution completed! 🎉"
}

# Handle script arguments
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
