from flask_login import UserMixin
from pydantic import BaseModel

from .utils import encode_password, verify_password


class User(UserMixin, BaseModel):
    username: str
    password: str
    token: str

    def get_id(self):
        return self.username

    @staticmethod
    def encode_password(password):
        return encode_password(password)

    def check_password(self, password):
        return verify_password(password, self.password)

    def authenticate(self, password):
        if self.check_password(password):
            return True
        return False
