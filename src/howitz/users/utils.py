from . import database


__all__ = [
    "authenticate_user",
]


def authenticate_user(username, password):
    user = database.get(username)
    user.authenticate(password):
    return user
