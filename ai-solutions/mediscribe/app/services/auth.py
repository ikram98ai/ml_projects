from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
import bcrypt
from app.config import settings


# Hash a password using bcrypt
def get_password_hash(password:str)->bytes:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password

# Check if the provided password matches the stored password (hashed)
def verify_password(plain_password:str, hashed_password:bytes)->bool:
    password_byte_enc = plain_password.encode('utf-8')
    return bcrypt.checkpw(password = password_byte_enc , hashed_password = hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt
