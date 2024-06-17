from pathlib import Path
import unittest

from howitz.users.model import User

TEST_DB = Path('testdb.sqlite3')


class UserTest(unittest.TestCase):

    def test_print_user_return_username(self):
        user = User(**{'username': 'foo', 'password': 'bar', 'token': 'xux'})
        self.assertEqual(str(user), 'username=foo password=SET token=SET')

    def test_autenticater_with_correct_password_returns_true(self):
        user = User(**{'username': 'foo', 'password': 'bar', 'token': 'xux'})
        user.password = User.encode_password('bar')
        result = user.authenticate('bar')
        self.assertTrue(result)

    def test_autenticater_with_wrong_password_returns_true(self):
        user = User(**{'username': 'foo', 'password': 'bar', 'token': 'xux'})
        user.password = User.encode_password('blbl')
        result = user.authenticate('bar')
        self.assertFalse(result)
