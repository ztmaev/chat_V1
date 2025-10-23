#!/bin/bash

# Docker startup script for Chat API
# This script helps with common Docker operations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if serviceAccountKey.json exists
if [ ! -f "serviceAccountKey.json" ]; then
    print_warn "serviceAccountKey.json not found!"
    print_warn "Please add your Firebase service account key before starting."
    print_warn "Download it from: Firebase Console → Project Settings → Service Accounts"
    read -p "Do you want to continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if .env file exists - copy from parent directory if needed
if [ ! -f ".env" ]; then
    print_warn ".env file not found in current directory"
    if [ -f "../.env" ]; then
        print_info "Copying .env from parent directory..."
        cp ../.env .env
        print_info ".env file copied successfully"
    elif [ -f ".env.example" ]; then
        print_info "Creating .env from .env.example..."
        cp .env.example .env
        print_warn "Please edit .env file and set ADMIN_USERNAME and ADMIN_PASSWORD"
    else
        print_error "No .env or .env.example found. Cannot proceed."
        exit 1
    fi
fi

# Parse command line arguments
COMMAND=${1:-start}

case $COMMAND in
    start)
        print_info "Starting Chat API..."
        docker-compose up -d
        print_info "Chat API is starting..."
        sleep 3
        docker-compose ps
        print_info "API should be available at http://localhost:5001"
        print_info "View logs with: docker-compose logs -f chat-api"
        ;;
    
    stop)
        print_info "Stopping Chat API..."
        docker-compose down
        print_info "Chat API stopped."
        ;;
    
    restart)
        print_info "Restarting Chat API..."
        docker-compose restart
        print_info "Chat API restarted."
        ;;
    
    logs)
        print_info "Showing logs (Ctrl+C to exit)..."
        docker-compose logs -f chat-api
        ;;
    
    build)
        print_info "Building Chat API container..."
        docker-compose build --no-cache
        print_info "Build complete."
        ;;
    
    rebuild)
        print_info "Rebuilding and restarting Chat API..."
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        print_info "Chat API rebuilt and started."
        ;;
    
    shell)
        print_info "Opening shell in Chat API container..."
        docker-compose exec chat-api bash
        ;;
    
    status)
        print_info "Chat API status:"
        docker-compose ps
        echo ""
        print_info "Health status:"
        docker inspect --format='{{.State.Health.Status}}' influencer-chat-api 2>/dev/null || echo "Container not running"
        ;;
    
    backup)
        print_info "Backing up database..."
        BACKUP_FILE="messaging.db.backup.$(date +%Y%m%d_%H%M%S)"
        docker-compose exec -T chat-api cat /app/messaging.db > "$BACKUP_FILE"
        print_info "Database backed up to: $BACKUP_FILE"
        ;;
    
    restore)
        if [ -z "$2" ]; then
            print_error "Please specify backup file: ./docker-start.sh restore <backup-file>"
            exit 1
        fi
        if [ ! -f "$2" ]; then
            print_error "Backup file not found: $2"
            exit 1
        fi
        print_info "Restoring database from: $2"
        docker-compose exec -T chat-api sh -c 'cat > /app/messaging.db' < "$2"
        docker-compose restart chat-api
        print_info "Database restored and API restarted."
        ;;
    
    init)
        print_info "Initializing database with demo data..."
        docker-compose exec chat-api python3 setup_demo_data.py
        print_info "Demo data initialized."
        ;;
    
    clean)
        print_warn "This will remove all containers, volumes, and images."
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Cleaning up..."
            docker-compose down -v
            docker system prune -f
            print_info "Cleanup complete."
        fi
        ;;
    
    help|*)
        echo "Chat API Docker Management Script"
        echo ""
        echo "Usage: ./docker-start.sh [command]"
        echo ""
        echo "Commands:"
        echo "  start             - Start the API"
        echo "  stop              - Stop the API"
        echo "  restart           - Restart the API"
        echo "  logs              - View API logs"
        echo "  build             - Build the Docker image"
        echo "  rebuild           - Rebuild and restart"
        echo "  shell             - Open shell in container"
        echo "  status            - Show container status"
        echo "  backup            - Backup database"
        echo "  restore <file>    - Restore database from backup"
        echo "  init              - Initialize database with demo data"
        echo "  clean             - Remove all containers and volumes"
        echo "  help              - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./docker-start.sh start              # Start the API"
        echo "  ./docker-start.sh logs               # View logs"
        echo "  ./docker-start.sh backup             # Backup database"
        echo "  ./docker-start.sh restore backup.db  # Restore database"
        echo ""
        echo "Configuration:"
        echo "  Edit .env file to customize settings (FLASK_ENV, ADMIN_USERNAME, etc.)"
        ;;
esac
