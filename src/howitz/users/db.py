import logging
import sqlite3

from .model import User


logger = logging.getLogger("__name__")


class UserDB:
    class DBException(Exception):
        pass

    def __init__(self, database_file: str):
        self.database_file = database_file

    @staticmethod
    def user_factory(cursor, row):
        fields = [column[0] for column in cursor.description]
        return User(**{k: v for k,v in zip(fields, row)})

    def initdb(self):
        field_items = []
        for field_name in User.model_fields.keys():
            field_string = f"{field_name} TEXT NOT NULL"
            if field_name == 'username':
                field_string += ' PRIMARY KEY'
            field_items.append(field_string)
        field_query = ', '.join(field_items)
        querystring = f"CREATE TABLE IF NOT EXISTS user ({field_query})"
        params = ()
        connection = self.change_db(querystring, params)
        connection.close()

    def connect(self):
        logger.debug('Connecting to %s', self.database_file)
        connection = sqlite3.connect(self.database_file, check_same_thread=False)
        connection.row_factory = self.user_factory
        return connection

    def change_db(self, querystring, params):
        connection = self.connect()
        with connection:
            connection.execute(querystring, params)
        return connection

    def change_and_return_user(self, username, querystring, params):
        connection = self.change_db(querystring, params)
        return self.get(username, connection)

    def get(self, username, connection=None):
        logger.debug('Getting user %s', username)
        if not connection:
            connection = self.connect()
        querystring = "SELECT * from user where username=?"
        params = (username,)
        query = connection.execute(querystring, params)
        result = query.fetchall()
        connection.close()
        if not result:
            logger.warn('User %s not in database',  username)
            return None
        if len(result) > 1:
            logger.error('Multiple %s in database!',  username)
            raise self.DBException("More than one with that username, b0rked database")
        return result[0]

    def add(self, user: User):
        querystring = "INSERT INTO user (username, password, token) values (?, ?, ?)"
        password = user.encode_password(user.password)
        params = (user.username, password, user.token)
        return self.change_and_return_user(user.username, querystring, params)

    def update(self, user: User):
        querystring = "REPLACE INTO user (username, password, token) values (?, ?, ?)"
        password = user.password
        # Do not reencrypt
        if not password.startswith(('scrypt:', 'pbkdf2:')):
            password = user.encode_password(password)
        params = (user.username, password, user.token)
        return self.change_and_return_user(user.username, querystring, params)

    def remove(self, username):
        querystring = "DELETE from user where username = ?"
        if not isinstance(username, str):
            username = username.username  # User-object sent in
        params = (username,)
        return self.change_and_return_user(username, querystring, params)

    def get_all(self):
        querystring = "SELECT username, password, token from user"
        connection = self.connect()
        query = connection.execute(querystring)
        result = query.fetchall()
        connection.close()
        if not result:
            return None
        return result
