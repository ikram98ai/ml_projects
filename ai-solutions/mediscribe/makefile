lint:
	uv run ruff check

fix:
	uv run ruff check --fix

format:
	uv run ruff format

init_db:
	uv run python manage.py init-db

destroy_db:
	uv run python manage.py delete-all-tables

user:
	uv run python manage.py create-user 
delete_user:
	uv run python manage.py delete-user

dev:
	uv run fastapi dev app/main.py