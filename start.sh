#!/bin/bash

# SuperAgent n8n - One-Command Setup Script
# Deploys a production-ready Discord bot with AI and memory

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REQUIRED_COMMANDS=("docker" "docker-compose")
ENV_FILE=".env"
COMPOSE_FILE="docker-compose.simple.yml"

echo "🚀 SuperAgent n8n - One-Command Setup"
echo "======================================"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if required commands exist
check_dependencies() {
    print_info "Checking dependencies..."
    
    for cmd in "${REQUIRED_COMMANDS[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            print_error "$cmd is not installed"
            echo "Please install Docker and Docker Compose:"
            echo "  - Docker: https://docs.docker.com/get-docker/"
            echo "  - Docker Compose: https://docs.docker.com/compose/install/"
            exit 1
        fi
    done
    
    print_status "All dependencies found"
}

# Check if .env file exists and has required variables
check_environment() {
    print_info "Checking environment configuration..."
    
    if [[ ! -f "$ENV_FILE" ]]; then
        print_warning ".env file not found, creating from template..."
        
        # Create .env file with template
        cat > "$ENV_FILE" << EOF
# Discord Configuration
DISCORD_TOKEN_GROK4=your_discord_bot_token_here
DEFAULT_SERVER_ID=your_discord_server_id_here

# AI API Keys
XAI_API_KEY=your_grok4_api_key_here

# Database Configuration (use these defaults)
POSTGRES_USER=superagent
POSTGRES_PASSWORD=superagent-db-2025
POSTGRES_DB=superagent

# n8n Configuration (optional)
N8N_PASSWORD=SuperAgent2025
EOF
        
        print_error "Please edit $ENV_FILE with your Discord bot token and Grok4 API key"
        print_info "Get Discord bot token: https://discord.com/developers/applications"
        print_info "Get Grok4 API key: https://x.ai"
        echo ""
        echo "After editing $ENV_FILE, run this script again:"
        echo "  ./start.sh"
        exit 1
    fi
    
    # Check if required variables are set
    source "$ENV_FILE"
    
    if [[ -z "$DISCORD_TOKEN_GROK4" || "$DISCORD_TOKEN_GROK4" == "your_discord_bot_token_here" ]]; then
        print_error "DISCORD_TOKEN_GROK4 not configured in $ENV_FILE"
        print_info "Get your Discord bot token from: https://discord.com/developers/applications"
        exit 1
    fi
    
    if [[ -z "$XAI_API_KEY" || "$XAI_API_KEY" == "your_grok4_api_key_here" ]]; then
        print_error "XAI_API_KEY not configured in $ENV_FILE"  
        print_info "Get your Grok4 API key from: https://x.ai"
        exit 1
    fi
    
    print_status "Environment configuration valid"
}

# Clean up old files and directories
cleanup_repository() {
    print_info "Cleaning up repository..."
    
    # Remove old virtual environments
    if [[ -d "discord-bot-venv" ]]; then
        print_info "Removing old virtual environment..."
        rm -rf discord-bot-venv
    fi
    
    if [[ -d ".venv" ]]; then
        print_info "Removing Python virtual environment (using Docker now)..."
        rm -rf .venv
    fi
    
    # Remove test files
    if [[ -f "test_api.json" ]]; then
        rm -f test_api.json
    fi
    
    # Remove old standalone scripts (we have combined service now)
    if [[ -f "discord_forwarder.py" ]]; then
        print_info "Moving old scripts to legacy..."
        mkdir -p legacy
        mv discord_forwarder.py legacy/ 2>/dev/null || true
        mv discord_api_server.py legacy/ 2>/dev/null || true
    fi
    
    print_status "Repository cleaned"
}

# Build and start services
start_services() {
    print_info "Building and starting services..."
    
    # Stop any existing services
    docker-compose -f "$COMPOSE_FILE" down 2>/dev/null || true
    
    # Build and start services
    print_info "Starting PostgreSQL and Redis..."
    docker-compose -f "$COMPOSE_FILE" up -d postgres redis
    
    # Wait for database to be ready
    print_info "Waiting for database to initialize..."
    for i in {1..30}; do
        if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U superagent -d superagent >/dev/null 2>&1; then
            break
        fi
        echo -n "."
        sleep 2
    done
    echo ""
    
    # Start Discord bot service
    print_info "Building and starting Discord bot..."
    docker-compose -f "$COMPOSE_FILE" up -d --build discord-bot
    
    print_status "All services started"
}

# Wait for services to be healthy
wait_for_health() {
    print_info "Waiting for services to be healthy..."
    
    # Wait for Discord bot to be ready
    for i in {1..30}; do
        if curl -s http://localhost:5001/health >/dev/null 2>&1; then
            break
        fi
        echo -n "."
        sleep 3
    done
    echo ""
    
    # Check final health status
    if curl -s http://localhost:5001/health >/dev/null 2>&1; then
        print_status "Discord bot is healthy"
    else
        print_error "Discord bot failed to start properly"
        print_info "Check logs with: docker-compose -f $COMPOSE_FILE logs discord-bot"
        exit 1
    fi
}

# Display success message and instructions
show_success() {
    echo ""
    echo "🎉 SuperAgent n8n Discord Bot is now running!"
    echo "============================================="
    echo ""
    print_status "Services Status:"
    echo "  📊 API Server:    http://localhost:5001/health"
    echo "  📊 Statistics:    http://localhost:5001/stats"
    echo "  🗄️  Database:      PostgreSQL on port 5436"
    echo "  💾 Cache:         Redis on port 6379"
    echo ""
    print_status "Testing the Bot:"
    echo "  1. Go to your Discord server"
    echo "  2. Mention your bot: @YourBot hello!"
    echo "  3. Or use keyword: hey grok, are you there?"
    echo ""
    print_status "Monitoring Commands:"
    echo "  View logs:        docker-compose -f $COMPOSE_FILE logs -f discord-bot"
    echo "  Check health:     curl http://localhost:5001/health"
    echo "  Check stats:      curl http://localhost:5001/stats"
    echo "  Stop services:    docker-compose -f $COMPOSE_FILE down"
    echo ""
    print_info "Your bot is now running with full memory and AI capabilities!"
    
    # Show bot stats if available
    if curl -s http://localhost:5001/stats >/dev/null 2>&1; then
        echo ""
        print_info "Current Bot Statistics:"
        curl -s http://localhost:5001/stats | python3 -m json.tool 2>/dev/null || echo "  (Stats endpoint available at http://localhost:5001/stats)"
    fi
}

# Advanced setup option
advanced_setup() {
    if [[ "$1" == "--advanced" ]]; then
        print_info "Starting advanced setup with n8n workflow engine..."
        docker-compose -f "$COMPOSE_FILE" --profile advanced up -d n8n
        
        echo ""
        print_status "Advanced Features Enabled:"
        echo "  🔄 n8n Workflows: http://localhost:5678 (admin / SuperAgent2025)"
        echo "  📝 Import workflows from: ./workflows/"
        print_info "n8n provides visual workflow management for advanced users"
    fi
}

# Main execution
main() {
    # Parse arguments
    ADVANCED_MODE=false
    if [[ "$1" == "--advanced" ]]; then
        ADVANCED_MODE=true
    fi
    
    # Run setup steps
    check_dependencies
    check_environment
    cleanup_repository
    start_services
    wait_for_health
    
    # Advanced setup if requested
    if [[ "$ADVANCED_MODE" == true ]]; then
        advanced_setup "--advanced"
    fi
    
    show_success
}

# Handle script interruption
trap 'print_error "Setup interrupted"; exit 1' INT

# Show help if requested
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "SuperAgent n8n - One-Command Setup"
    echo ""
    echo "Usage:"
    echo "  ./start.sh           # Simple setup (recommended)"
    echo "  ./start.sh --advanced # Include n8n workflows"
    echo "  ./start.sh --help    # Show this help"
    echo ""
    echo "Prerequisites:"
    echo "  - Docker and Docker Compose installed"
    echo "  - Discord bot token (from Discord Developer Portal)"
    echo "  - Grok4 API key (from x.ai)"
    echo ""
    echo "The script will:"
    echo "  1. Check dependencies and environment"
    echo "  2. Clean up old files"
    echo "  3. Start PostgreSQL and Redis"
    echo "  4. Build and start Discord bot"
    echo "  5. Wait for services to be healthy"
    echo "  6. Display success message and monitoring info"
    exit 0
fi

# Run main function
main "$@"