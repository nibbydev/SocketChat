import sqlite3


class Database:
    def __init__(self, name):
        self.name = name

        self.connection = None
        self.c = None

        self.__connect()

    def __connect(self):
        self.connection = sqlite3.connect(self.name)
        self.c = self.connection.cursor()

        self.__verify_database()

    def __verify_database(self):
        row = self.c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()

        if row is None or "users" not in row:
            self.c.execute("CREATE TABLE users (date TEXT, name TEXT, password TEXT, email TEXT, is_admin INT)")

            # Add default root account
            self.c.execute("INSERT INTO users VALUES ('-','root','clearTextPasswordsAreBad','admin@test.com',1)")

            self.connection.commit()

            print("Created base db structure")

    def close(self):
        self.connection.close()


def init():
    database = Database("test.db")

    database.close()


if __name__ == "__main__":
    init()
