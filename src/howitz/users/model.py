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

    def check_password(self, password):
        # needs much magic!
        return self.password == password

    def login(self, password):
        if self.check_password(password):
            self._authenticated = True
            return True
        return False
