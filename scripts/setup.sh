#!/bin/bash

# SuperAgent n8n - Automated Setup Script
# This script sets up the complete SuperAgent n8n environment

set -e  # Exit on any error

echo "🚀 SuperAgent n8n - Automated Setup"
echo "===================================="

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

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Setup environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f .env ]; then
        cp .env.example .env
        print_warning "Created .env file from template"
        print_warning "Please edit .env with your API keys and tokens before proceeding"
        
        # Generate random passwords
        POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
        REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
        N8N_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
        N8N_ENCRYPTION_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
        
        # Update .env with generated passwords
        sed -i.bak "s/your_secure_postgres_password_here/$POSTGRES_PASSWORD/" .env
        sed -i.bak "s/your_redis_password_here/$REDIS_PASSWORD/" .env
        sed -i.bak "s/your_n8n_admin_password_here/$N8N_PASSWORD/" .env
        sed -i.bak "s/your_32_character_encryption_key_here/$N8N_ENCRYPTION_KEY/" .env
        
        rm .env.bak
        
        print_success "Generated secure passwords for services"
        print_warning "n8n admin password: $N8N_PASSWORD"
        print_warning "Save this password! You'll need it to access n8n interface"
    else
        print_success ".env file already exists"
    fi
}

# Start Docker services
start_services() {
    print_status "Starting Docker services..."
    
    # Create necessary directories
    mkdir -p workflows/agents
    mkdir -p docker
    
    # Start services
    docker-compose -f docker/docker-compose.yml up -d
    
    print_success "Docker services started"
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    
    # Wait for PostgreSQL
    print_status "Waiting for PostgreSQL..."
    for i in {1..30}; do
        if docker-compose -f docker/docker-compose.yml exec -T postgres pg_isready -U superagent -d superagent_n8n &> /dev/null; then
            print_success "PostgreSQL is ready"
            break
        fi
        sleep 2
        if [ $i -eq 30 ]; then
            print_error "PostgreSQL failed to start within 60 seconds"
            exit 1
        fi
    done
    
    # Wait for Redis
    print_status "Waiting for Redis..."
    for i in {1..30}; do
        if docker-compose -f docker/docker-compose.yml exec -T redis redis-cli ping &> /dev/null; then
            print_success "Redis is ready"
            break
        fi
        sleep 2
        if [ $i -eq 30 ]; then
            print_error "Redis failed to start within 60 seconds"
            exit 1
        fi
    done
    
    # Wait for n8n
    print_status "Waiting for n8n..."
    for i in {1..60}; do
        if curl -f http://localhost:5678/healthz &> /dev/null; then
            print_success "n8n is ready"
            break
        fi
        sleep 2
        if [ $i -eq 60 ]; then
            print_error "n8n failed to start within 120 seconds"
            exit 1
        fi
    done
}

# Verify setup
verify_setup() {
    print_status "Verifying setup..."
    
    # Check service status
    local services=("postgres" "redis" "n8n" "healthcheck")
    for service in "${services[@]}"; do
        if docker-compose -f docker/docker-compose.yml ps $service | grep -q "Up"; then
            print_success "$service is running"
        else
            print_error "$service is not running"
            return 1
        fi
    done
    
    # Check database connection
    if docker-compose -f docker/docker-compose.yml exec -T postgres psql -U superagent -d superagent_n8n -c "SELECT 1;" &> /dev/null; then
        print_success "Database connection successful"
    else
        print_error "Database connection failed"
        return 1
    fi
    
    # Check Redis connection
    if docker-compose -f docker/docker-compose.yml exec -T redis redis-cli ping | grep -q "PONG"; then
        print_success "Redis connection successful"
    else
        print_error "Redis connection failed"
        return 1
    fi
    
    # Check n8n interface
    if curl -f http://localhost:5678 &> /dev/null; then
        print_success "n8n interface accessible"
    else
        print_error "n8n interface not accessible"
        return 1
    fi
}

# Display next steps
show_next_steps() {
    print_success "Setup completed successfully!"
    echo ""
    echo "🎉 Next Steps:"
    echo "=============="
    echo ""
    echo "1. 📝 Configure your .env file with API keys:"
    echo "   - DISCORD_TOKEN_GROK4"
    echo "   - XAI_API_KEY"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - GOOGLE_AI_API_KEY"
    echo "   - DEFAULT_SERVER_ID"
    echo ""
    echo "2. 🌐 Access n8n interface:"
    echo "   URL: http://localhost:5678"
    echo "   Username: admin"
    echo "   Password: $(grep N8N_BASIC_AUTH_PASSWORD .env | cut -d'=' -f2)"
    echo ""
    echo "3. 📥 Import workflows:"
    echo "   - Go to n8n interface"
    echo "   - Import workflows/*.json files"
    echo ""
    echo "4. 🔗 Configure Discord webhooks:"
    echo "   - Copy webhook URL from n8n"
    echo "   - Set up Discord server webhook"
    echo ""
    echo "5. 🧪 Test the bot:"
    echo "   - Send @Grok4Agent hello in Discord"
    echo "   - Check n8n execution logs"
    echo ""
    echo "📊 Service URLs:"
    echo "- n8n: http://localhost:5678"
    echo "- Health Check: http://localhost:8080"
    echo "- PostgreSQL: localhost:5432"
    echo "- Redis: localhost:6379"
    echo ""
    echo "📋 Useful Commands:"
    echo "- View logs: docker-compose -f docker/docker-compose.yml logs -f"
    echo "- Stop services: docker-compose -f docker/docker-compose.yml down"
    echo "- Restart services: docker-compose -f docker/docker-compose.yml restart"
    echo ""
    print_success "Happy chatbot building! 🤖"
}

# Handle errors
handle_error() {
    print_error "Setup failed at step: $1"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "- Check Docker is running: docker info"
    echo "- Check logs: docker-compose -f docker/docker-compose.yml logs"
    echo "- Reset and retry: docker-compose -f docker/docker-compose.yml down && ./scripts/setup.sh"
    echo ""
    echo "For help, check docs/SETUP.md or create an issue on GitHub"
    exit 1
}

# Main execution
main() {
    print_status "Starting SuperAgent n8n setup..."
    
    check_prerequisites || handle_error "Prerequisites check"
    setup_environment || handle_error "Environment setup"
    start_services || handle_error "Service startup"
    verify_setup || handle_error "Setup verification"
    
    show_next_steps
}

# Run main function
main "$@"