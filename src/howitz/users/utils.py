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


def update_token(user, challenge, secret):
    # copied from ritz implementation
    gen_token = "%s %s" % (challenge, secret)
    auth_token = hashlib.sha1(gen_token.encode('UTF-8')).hexdigest()

    endpoints.database.update_token(user.username, auth_token)
