from flask_login import UserMixin
from pydantic import BaseModel


class User(UserMixin, BaseModel):
    username: str
    password: str
    token: str

    def get_id(self):
        return self.username
