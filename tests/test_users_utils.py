from pathlib import Path
import unittest

from howitz.users.db import UserDB
from howitz.users.model import User
from howitz.users.utils import authenticate_user

TEST_DB = Path('testdb.sqlite3')


class UserUtilsTest(unittest.TestCase):

    def setUp(self):
        self.userdb = UserDB(TEST_DB)
        self.userdb.initdb()

    def tearDown(self):
        TEST_DB.unlink(missing_ok=True)

    def test_autenticate_user_with_correct_password_returns_true(self):
        user = User(**{'username': 'foo', 'password': 'bar', 'token': 'xux'})
        resuser = self.userdb.add(user)
        result = authenticate_user(self.userdb, 'foo', 'bar')
        self.assertTrue(result)

    def test_autenticate_user_with_wromg_password_returns_false(self):
        user = User(**{'username': 'foo', 'password': 'bar', 'token': 'xux'})
        resuser = self.userdb.add(user)
        result = authenticate_user(self.userdb, 'foo', 'blbl')
        self.assertFalse(result)
