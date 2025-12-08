lint:
	uv run ruff check

fix:
	uv run ruff check --fix

format:
	uv run ruff format

init-db:
	uv run python manage.py init-db

destroy-db:
	uv run python manage.py delete-all-tables

user:
	uv run python manage.py create-user 

delete-user:
	uv run python manage.py delete-user

build:
	cd web && npm run build

dev-web:
	cd web && npm run dev

dev:
	uv run fastapi dev app/main.py