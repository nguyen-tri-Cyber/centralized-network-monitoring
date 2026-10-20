# Centralized Network Monitoring System - Makefile
.PHONY: help up down restart logs validate test clean

help:
	@echo "Centralized Network Monitoring System - Commands:"
	@echo "  make up        Start the Docker Compose monitoring stack"
	@echo "  make down      Stop the monitoring stack"
	@echo "  make restart   Restart all monitoring services"
	@echo "  make logs      View aggregated logs from all services"
	@echo "  make validate  Validate configurations, schemas, and linting"
	@echo "  make test      Execute unit tests for anomaly detection and configs"
	@echo "  make clean     Stop stack and remove volumes"

up:
	bash scripts/up.sh

down:
	bash scripts/down.sh

restart: down up

logs:
	docker compose -f deploy/docker-compose.yml logs -f

validate:
	python3 scripts/validate.py

test:
	python3 -m unittest discover -s tests -v

clean:
	docker compose -f deploy/docker-compose.yml down -v
