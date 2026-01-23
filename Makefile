.PHONY: up down logs dev

up:
	docker compose -f deploy/docker-compose.yml up --build

dev:
	docker compose -f deploy/docker-compose.dev.yml up --build

down:
	docker compose -f deploy/docker-compose.yml down

logs:
	docker compose -f deploy/docker-compose.yml logs -f
