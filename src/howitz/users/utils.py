import hashlib

from werkzeug.security import generate_password_hash, check_password_hash

from .. import endpoints


__all__ = [
    "authenticate_user",
    "encode_password",
    "verify_password",
]


def authenticate_user(username: str, password: str):
    user = endpoints.database.get(username)
    if user and user.authenticate(password):
        return user
    return None


def encode_password(password: str):
    return generate_password_hash(password, "scrypt")


def verify_password(password: str, password_hash: str):
    return check_password_hash(password_hash, password)
