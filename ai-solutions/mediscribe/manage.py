import typer
from app.models import User, Transcript, Chat
from app.services.auth import get_password_hash

app = typer.Typer()


# Database management commands
@app.command()
def init_db():
    """Initialize all database tables"""
    tables = [("User", User), ("Transcript", Transcript), ("Chat", Chat)]

    for table_name, model in tables:
        try:
            if not model.exists():
                typer.echo(f"Creating {table_name} table...")
                model.create_table(
                    read_capacity_units=1, write_capacity_units=1, wait=True
                )
                typer.secho(f"✓ {table_name} table created.", fg=typer.colors.GREEN)
            else:
                typer.secho(
                    f"✓ {table_name} table already exists.", fg=typer.colors.BLUE
                )
        except Exception as e:
            typer.secho(
                f"✗ Error creating {table_name} table: {e}", fg=typer.colors.RED
            )


@app.command()
def delete_all_tables():
    """Delete all database tables"""
    if not typer.confirm("Are you sure you want to delete all tables?"):
        typer.echo("Cancelled.")
        return

    tables = [("Chat", Chat), ("Transcript", Transcript), ("User", User)]

    for table_name, model in tables:
        try:
            if model.exists():
                typer.echo(f"Deleting {table_name} table...")
                model.delete_table()
                typer.secho(f"✓ {table_name} table deleted.", fg=typer.colors.GREEN)
            else:
                typer.secho(
                    f"✓ {table_name} table does not exist.", fg=typer.colors.BLUE
                )
        except Exception as e:
            typer.secho(
                f"✗ Error deleting {table_name} table: {e}", fg=typer.colors.RED
            )


@app.command()
def create_user(
    username: str = typer.Option(..., prompt=True, help="Username"),
    password: str = typer.Option(
        ..., prompt=True, hide_input=True, confirmation_prompt=True, help="Password"
    ),
    role: str = typer.Option("clinician", prompt=True, help="User role"),
):
    """Create a new user (will prompt for missing values)"""
    try:
        if not User.exists():
            User.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)

        # If you have a different uniqueness check, replace this
        try:
            User.get(username)
            typer.secho(f"✗ User '{username}' already exists.", fg=typer.colors.RED)
            return
        except User.DoesNotExist:
            pass

        user = User(
            username=username,
            password_hash=get_password_hash(password),
            role=role,
        )
        user.save()
        typer.secho(f"✓ User '{username}' created successfully.", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"✗ Error creating user: {e}", fg=typer.colors.RED)


@app.command()
def delete_user(username: str = typer.Option(..., prompt=True, help="Username")):
    """Delete a user (prompts for username if not provided)"""
    if not typer.confirm(f"Are you sure you want to delete user '{username}'?"):
        typer.echo("Cancelled.")
        return

    try:
        user = User.get(username)
        user.delete()
        typer.secho(f"✓ User '{username}' deleted successfully.", fg=typer.colors.GREEN)
    except User.DoesNotExist:
        typer.secho(f"✗ User '{username}' not found.", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"✗ Error deleting user: {e}", fg=typer.colors.RED)


@app.command()
def list_users():
    """List all users"""
    try:
        users = User.scan()
        user_list = list(users)

        if not user_list:
            typer.echo("No users found.")
            return

        typer.echo("\nUsers:")
        for user in user_list:
            typer.echo(f"  • {user.username} (role: {user.role})")
        typer.echo(f"\nTotal: {len(user_list)} users")
    except Exception as e:
        typer.secho(f"✗ Error listing users: {e}", fg=typer.colors.RED)


if __name__ == "__main__":
    app()
