from flask_login import UserMixin
from pydantic import BaseModel


class User(UserMixin, BaseModel):
    username: str
    password: str
    token: str
    _authenticated = False

    def __init__(self, username, password, token):
        super().__init__(username=username, password=password, token=token)

    def __repr__(self):
        return "User" + str(self.id)

    def get_id(self):
        return self.username

    @property
    def is_authenticated(self):
        return self.is_active and self._authenticated

    @staticmethod
    def encode_password(password):
        # needs much magic!
        return password

    def check_password(self, password):
        return self.password == self.encode_password(password)

    def authenticate(self, password):
        if self.check_password(password):
            self._authenticated = True
            return True
        return False

    def log_out(self):
        # hide the magic attribute
        self._authenticated = False
