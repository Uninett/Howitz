from pathlib import Path
import unittest

from howitz.users.db import UserDB
from howitz.users.model import User

TEST_DB = Path('testdb.sqlite3')


class UserDBInitTest(unittest.TestCase):

    def test_create_database(self):
        userdb = UserDB(TEST_DB)
        userdb.initdb()


class UserDBTest(unittest.TestCase):

    def setUp(self):
        self.userdb = UserDB(TEST_DB)
        self.userdb.initdb()

    def tearDown(self):
        TEST_DB.unlink(missing_ok=True)

    def test_get_non_existent_user_returns_None(self):
        resuser = self.userdb.get('vfghtryvgbnhyubgnhjkbgnhjkvbgfhjufcgvhtjy')
        self.assertEqual(resuser, None)

    def test_remove_non_existent_user_returns_None(self):
        resuser = self.userdb.remove('vfghtryvgbnhyubgnhjkbgnhjkvbgfhjufcgvhtjy')
        self.assertEqual(resuser, None)
        resuser = self.userdb.get('vfghtryvgbnhyubgnhjkbgnhjkvbgfhjufcgvhtjy')
        self.assertEqual(resuser, None)

    def test_add_user(self):
        user = User(**{'username': 'foo', 'password': 'bar', 'token': 'xux'})
        resuser = self.userdb.add(user)
        self.assertEqual(user, resuser)

    def test_remove_existent_user(self):
        user = User(**{'username': 'foo', 'password': 'bar', 'token': 'xux'})
        resuser = self.userdb.add(user)
        resuser = self.userdb.remove(user.username)
        self.assertEqual(resuser, None)
        resuser = self.userdb.get('vfghtryvgbnhyubgnhjkbgnhjkvbgfhjufcgvhtjy')
        self.assertEqual(resuser, None)

    def test_update_non_existent_user_adds_user(self):
        user = User(**{'username': 'foo', 'password': 'bar', 'token': 'xux'})
        resuser = self.userdb.update(user)
        self.assertEqual(user, resuser)

    def test_get_all_when_no_users_should_return_None(self):
        result = self.userdb.get_all()
        self.assertEqual(result, None)

    def test_get_all_lists_all_usernames(self):
        user1 = User(**{'username': 'foo', 'password': 'bar', 'token': 'xux'})
        self.userdb.add(user1)
        user2 = User(**{'username': 'bar', 'password': 'xux', 'token': 'gurba'})
        self.userdb.add(user2)
        results = self.userdb.get_all()
        self.assertEqual(len(results), 2)
        print(results)

