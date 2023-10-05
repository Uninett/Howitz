from flask_login import UserMixin
from pydantic import BaseModel


class User(UserMixin, BaseModel):
    username: str
    password: str
    token: str

    def __init__(self, username, password, token):
        super().__init__(username=username, password=password, token=token)

    def __repr__(self):
        return "User" + str(self.id)

    def get_id(self):
        return self.username
