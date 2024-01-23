import hashlib

from werkzeug.exceptions import Forbidden
from werkzeug.security import generate_password_hash, check_password_hash


__all__ = [
    "authenticate_user",
    "encode_password",
    "verify_password",
]


def authenticate_user(database, username: str, password: str):
    user = database.get(username)
    if user and user.authenticate(password):
        return user
    else:
        raise Forbidden('Wrong username or password')


def encode_password(password: str):
    return generate_password_hash(password, "scrypt")


def verify_password(password: str, password_hash: str):
    return check_password_hash(password_hash, password)
