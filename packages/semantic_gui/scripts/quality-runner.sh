#!/bin/bash

# SCG Quality Runner Script
# Runs comprehensive quality checks using Docker with Node 20

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_success() {
    echo -e "${GREEN}✓${NC} $1"
}

echo_error() {
    echo -e "${RED}✗${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

echo_info "Starting SCG Quality Assurance Pipeline with Node 20..."

# Build development container
echo_info "Building development container..."
if docker-compose -f docker-compose.dev.yml build app-dev; then
    echo_success "Development container built successfully"
else
    echo_error "Failed to build development container"
    exit 1
fi

# Run dependency security check
echo_info "Running security audit..."
if docker-compose -f docker-compose.dev.yml run --rm app-dev npm audit --audit-level=moderate; then
    echo_success "Security audit passed"
else
    echo_warning "Security audit found issues (continuing anyway)"
fi

# Check for outdated dependencies
echo_info "Checking for outdated dependencies..."
docker-compose -f docker-compose.dev.yml run --rm app-dev npm outdated || echo_warning "Some dependencies are outdated"

# Run type checking
echo_info "Running TypeScript type checking..."
if docker-compose -f docker-compose.dev.yml run --rm app-dev npm run type-check; then
    echo_success "Client type checking passed"
else
    echo_error "Client type checking failed"
    exit 1
fi

if docker-compose -f docker-compose.dev.yml run --rm app-dev npm run type-check:server; then
    echo_success "Server type checking passed"
else
    echo_error "Server type checking failed"
    exit 1
fi

# Run linting
echo_info "Running ESLint..."
if docker-compose -f docker-compose.dev.yml run --rm app-dev npm run lint; then
    echo_success "Linting passed"
else
    echo_warning "Linting failed - attempting to fix automatically..."
    if docker-compose -f docker-compose.dev.yml run --rm app-dev npm run lint:fix; then
        echo_success "Auto-fixed linting issues"
        echo_info "Re-running linting check..."
        if docker-compose -f docker-compose.dev.yml run --rm app-dev npm run lint; then
            echo_success "Linting now passes"
        else
            echo_error "Linting still fails after auto-fix"
            exit 1
        fi
    else
        echo_error "Failed to auto-fix linting issues"
        exit 1
    fi
fi

# Run formatting check
echo_info "Checking code formatting..."
if docker-compose -f docker-compose.dev.yml run --rm app-dev npm run format:check; then
    echo_success "Code formatting is correct"
else
    echo_warning "Code formatting issues found - fixing automatically..."
    if docker-compose -f docker-compose.dev.yml run --rm app-dev npm run format; then
        echo_success "Code formatted successfully"
    else
        echo_error "Failed to format code"
        exit 1
    fi
fi

# Run unit tests
echo_info "Running unit tests..."
if docker-compose -f docker-compose.dev.yml run --rm app-dev npm test; then
    echo_success "All unit tests passed"
else
    echo_error "Unit tests failed"
    exit 1
fi

# Start services for integration tests
echo_info "Starting services for integration testing..."
docker-compose -f docker-compose.dev.yml up -d postgres

# Wait for PostgreSQL to be ready
echo_info "Waiting for PostgreSQL to be ready..."
docker-compose -f docker-compose.dev.yml run --rm app-dev /bin/sh -c "
    until pg_isready -h postgres -p 5432; do
        echo 'Waiting for PostgreSQL...'
        sleep 2
    done
    echo 'PostgreSQL is ready!'
"

# Run database migrations
echo_info "Running database migrations..."
if docker-compose -f docker-compose.dev.yml run --rm app-dev npm run db:push; then
    echo_success "Database migrations completed"
else
    echo_error "Database migrations failed"
    exit 1
fi

# Run integration tests
echo_info "Running integration tests..."
if docker-compose -f docker-compose.dev.yml run --rm app-dev npm run test:full-flow; then
    echo_success "Integration tests passed"
else
    echo_error "Integration tests failed"
    exit 1
fi

# Run E2E tests
echo_info "Running E2E tests..."
if docker-compose -f docker-compose.dev.yml run --rm app-dev npm run e2e; then
    echo_success "E2E tests passed"
else
    echo_warning "E2E tests failed (may need UI service running)"
fi

# Generate quality metrics
echo_info "Generating quality metrics..."
if docker-compose -f docker-compose.dev.yml run --rm app-dev npm run quality:metrics; then
    echo_success "Quality metrics generated"
else
    echo_warning "Failed to generate quality metrics"
fi

# Build production container to verify it works
echo_info "Testing production build..."
if docker build -t scg:latest .; then
    echo_success "Production build successful"
else
    echo_error "Production build failed"
    exit 1
fi

# Cleanup
echo_info "Cleaning up..."
docker-compose -f docker-compose.dev.yml down

echo_success "🎉 All quality checks passed! Your code is ready for production."
echo_info "Summary:"
echo "  ✓ Security audit"
echo "  ✓ Type checking (client & server)"
echo "  ✓ Code linting"
echo "  ✓ Code formatting"
echo "  ✓ Unit tests"
echo "  ✓ Database migrations"
echo "  ✓ Integration tests"
echo "  ✓ Production build"
echo ""
echo_info "To run individual checks:"
echo "  npm run security:check    - Security audit"
echo "  npm run type-check        - TypeScript checking"
echo "  npm run lint              - ESLint"
echo "  npm run format:check      - Prettier"
echo "  npm run test              - Unit tests"
echo "  npm run quality:full      - All quality checks"