.PHONY: help build start stop restart logs status shell test backup restore init clean dev prod

# Default target
help:
	@echo "Chat API Docker Management"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  build      - Build Docker image"
	@echo "  start      - Start containers (detached mode)"
	@echo "  dev        - Start containers (foreground mode)"
	@echo "  stop       - Stop containers"
	@echo "  restart    - Restart containers"
	@echo "  logs       - View container logs"
	@echo "  status     - Show container status"
	@echo "  shell      - Open shell in container"
	@echo "  test       - Run Docker setup tests"
	@echo "  backup     - Backup database"
	@echo "  restore    - Restore database (requires BACKUP_FILE=path)"
	@echo "  init       - Initialize database with demo data"
	@echo "  clean      - Remove containers and volumes"
	@echo ""
	@echo "Configuration: Edit .env file to customize settings"
	@echo ""

# Build Docker image
build:
	@echo "Building Docker image..."
	docker-compose build --no-cache

# Start containers
start:
	@echo "Starting Chat API..."
	docker-compose up -d
	@echo "API available at http://localhost:5001"
	@echo "View logs: make logs"

# Start in foreground (for development)
dev:
	@echo "Starting Chat API (foreground mode)..."
	docker-compose up
	@echo "API available at http://localhost:5001"

# Alias for start (for backward compatibility)
prod: start

# Stop containers
stop:
	@echo "Stopping Chat API..."
	docker-compose down

# Restart containers
restart:
	@echo "Restarting Chat API..."
	docker-compose restart

# View logs
logs:
	docker-compose logs -f chat-api

# Show container status
status:
	@echo "Container status:"
	@docker-compose ps
	@echo ""
	@echo "Health status:"
	@docker inspect --format='{{.State.Health.Status}}' influencer-chat-api 2>/dev/null || echo "Container not running"
	@echo ""
	@echo "Resource usage:"
	@docker stats --no-stream influencer-chat-api 2>/dev/null || echo "Container not running"

# Open shell in container
shell:
	@echo "Opening shell in Chat API container..."
	docker-compose exec chat-api bash

# Run tests
test:
	@echo "Running Docker setup tests..."
	./test-docker-setup.sh

# Backup database
backup:
	@echo "Backing up database..."
	@BACKUP_FILE="messaging.db.backup.$$(date +%Y%m%d_%H%M%S)" && \
	docker-compose exec -T chat-api cat /app/messaging.db > $$BACKUP_FILE && \
	echo "Database backed up to: $$BACKUP_FILE"

# Restore database
restore:
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Error: Please specify BACKUP_FILE=path"; \
		echo "Example: make restore BACKUP_FILE=messaging.db.backup.20251012_120000"; \
		exit 1; \
	fi
	@if [ ! -f "$(BACKUP_FILE)" ]; then \
		echo "Error: Backup file not found: $(BACKUP_FILE)"; \
		exit 1; \
	fi
	@echo "Restoring database from: $(BACKUP_FILE)"
	@docker-compose exec -T chat-api sh -c 'cat > /app/messaging.db' < $(BACKUP_FILE)
	@docker-compose restart chat-api
	@echo "Database restored and API restarted."

# Initialize database with demo data
init:
	@echo "Initializing database with demo data..."
	docker-compose exec chat-api python3 setup_demo_data.py
	@echo "Demo data initialized."

# Clean up everything
clean:
	@echo "Warning: This will remove all containers, volumes, and images."
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "Cleaning up..."; \
		docker-compose down -v; \
		docker system prune -f; \
		echo "Cleanup complete."; \
	else \
		echo "Cancelled."; \
	fi

# Rebuild and restart
rebuild: build start
	@echo "Rebuild complete."

# Quick development workflow
quick: stop build start logs
	@echo "Quick restart complete."
