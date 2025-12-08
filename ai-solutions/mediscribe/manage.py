from app.models.user import User
from app.models.transcript import Transcript
from app.services.auth import get_password_hash
import sys

def init_db():
    if not User.exists():
        print("Creating User table...")
        User.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
        print("User table created.")
    else:
        print("User table already exists.")

    if not Transcript.exists():
        print("Creating Transcript table...")
        Transcript.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
        print("Transcript table created.")
    else:
        print("Transcript table already exists.")


def create_user(username, password):
    if not User.exists():
        User.create_table(read_capacity_units=1, write_capacity_units=1)
    
    if User.count(username) > 0:
        print(f"User {username} already exists.")
        return

    user = User(
        username=username,
        password_hash=get_password_hash(password),
        role="clinician"
    )
    user.save()
    print(f"User {username} created successfully.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python create_user.py <username> <password>")
    else:
        init_db()
        create_user(sys.argv[1], sys.argv[2])
