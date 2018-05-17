from threading import Thread
import sqlite3
import socket

"""
Headers:
    'disconnect' - a client disconnected
    'bye' - that client requested a disconnect
    'message' - a text message
    'welcome' - indicating a client it may join
    'connected' - a new client joined
    'couldn't connect' - server full or something, a client couldn't connect
    'full' - indicating a client the server is full
    'exit' - the clients MUST disconnect
"""


MAX_MSG_LENGTH = 2056


class Database:
    def __init__(self, name):
        self.name = name

        self.connection = None
        self.c = None

        self.__connect()

    def __connect(self):
        self.connection = sqlite3.connect(self.name, check_same_thread=False)
        self.c = self.connection.cursor()

        self.__verify_database()

    def close(self):
        self.connection.commit()
        self.connection.close()

    # ======================================================================================================
    # Initial database creation
    # ======================================================================================================

    def __verify_database(self):
        row = self.c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()

        if row is None or "users" not in row:
            self.__create_table_users()
            self.__create_table_channels()

            self.connection.commit()
            print("Created base db structure")

    def __create_table_users(self):
        asd = "CREATE TABLE users (date TEXT, username TEXT, nick TEXT, password TEXT, rank INT, mute INT, ban INT)"
        self.c.execute(asd)

        data = [
            ("-", "root", "root", "123", 0, 0, 0),
            ("-", "1", "1", "Password", 99, 0, 0)
        ]
        self.c.executemany("INSERT INTO users VALUES (?,?,?,?,?,?,?)", data)

    def __create_table_channels(self):
        self.c.execute("CREATE TABLE channels (name TEXT, password TEXT, rank INT)")

        # Add default channels
        data = [
            ("general", "", 99),
            ("off-topic", "", 99),
            ("music", "", 99),
            ("admin", "123", 0)
        ]
        self.c.executemany("INSERT INTO channels VALUES (?,?,?)", data)

    # ======================================================================================================
    # User management
    # ======================================================================================================

    def check_username_exists(self, username):
        row = self.c.execute("SELECT * FROM users WHERE username=?", (username,))
        entry = row.fetchone()

        return entry is not None

    def check_login(self, username, password):
        row = self.c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        return row.fetchone()

    def create_user(self, username, password):
        if self.check_username_exists(username):
            return False

        data = ("today", username, username, password, 99, 0, 0)
        self.c.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?)", data)

        self.connection.commit()

        return True


class Client:
    def __init__(self, server, connection, address):
        self.server = server
        self.connection = connection
        self.address = address
        self.client_id = None
        self.thread = None

        self.logged_in = False

        self.username = None
        self.nick = None
        self.rank = None
        self.mute = None

    # ======================================================================================================
    # Receive and process messages
    # ======================================================================================================

    def __loop_receive(self):
        self.send_data("!login", "please send login info")

        try:
            while True:
                data = self.connection.recv(MAX_MSG_LENGTH).decode("utf-8").split(" ", 1)

                self._sort_data(data[0], data[1])
        except ConnectionResetError:
            pass
        finally:
            self.stop()

    def _sort_data(self, cmd, content):
        if not self.logged_in:
            self._process_login(cmd, content)
            return

        if cmd == "!msg":
            print("[{0}] {1} ({2}:{3}): '{4}'".format(
                self.client_id,
                self.username,
                self.address[0],
                self.address[1],
                content
            ))
        elif cmd == "!kick":
            print("Not implemented")

    def _process_login(self, cmd, content):
        if cmd == "!login":
            try:
                username = content.split(" ")[0]
                password = content.split(" ")[1]
            except IndexError:
                self.send_data("!error", "invalid info provided")
                self.logged_in = False
                return

            user_data = self.server.database.check_login(username, password)

            if user_data is None:
                self.send_data("!error", "invalid username or password")
                self.logged_in = False
                return
            elif user_data[6] is 1:
                self.send_data("!error", "you are banned")
                self.logged_in = False
                return

            self.send_data("!success", "logged in successfully")
            self.logged_in = True

            self.username = user_data[1]
            self.nick = user_data[2]
            self.rank = user_data[4]
            self.mute = user_data[5]

        elif cmd == "!register":
            try:
                username = content.split(" ")[0]
                password = content.split(" ")[1]
            except IndexError:
                self.send_data("!error", "invalid info provided")
                self.logged_in = False
                return

            self.logged_in = self.server.database.create_user(username, password)

            if self.logged_in:
                self.send_data("!success", "account created successfully")
            else:
                self.send_data("!error", "username already in use")

    # ======================================================================================================
    # Send data
    # ======================================================================================================

    def send_data(self, cmd, content):
        payload = cmd + " " + content

        try:
            self.connection.send(payload.encode("utf-8"))
        except ConnectionResetError:
            pass

    # ======================================================================================================
    # Control functions
    # ======================================================================================================

    def run(self, client_id):
        self.client_id = client_id

        self.thread = Thread(
            target=self.__loop_receive,
            name="client-" + str(self.client_id),
            daemon=True
        )

        self.thread.start()

    def stop(self):
        msg = "Client {0} ({1}:{2}) disconnected".format(self.client_id, self.address[0], self.address[1])
        self.server.send_data_to_all(self, "!disconnect", msg)
        print(msg)

        self.connection.close()
        self.server.clients.remove(self)

    # ======================================================================================================
    # Utility functions
    # ======================================================================================================


class Server:
    def __init__(self, database, ip, port, max_clients):
        self.ip = ip
        self.port = port
        self.max_clients = max_clients
        self.clients = []

        self.database = database
        self.connection = None

    # ======================================================================================================
    # Receive and process clients
    # ======================================================================================================

    def __receive_loop(self):
        while True:
            connection, address = self.connection.accept()
            client = Client(self, connection, address)

            self.clients.append(client)
            client_id = self.clients.index(client)
            client.run(client_id)

    # ======================================================================================================
    # Send data
    # ======================================================================================================

    def send_data_to_all(self, sender, cmd, content):
        for client in self.clients:
            if client != sender:
                client.send_data(cmd, content)

    # ======================================================================================================
    # Control functions
    # ======================================================================================================

    def run(self):
        print("Starting server on '" + self.ip + "':'" + str(self.port) + "'")

        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.bind((self.ip, self.port))

        # Specifying max connections here doesn't really seem to work for some reason
        self.connection.listen(self.max_clients)

        print("Awaiting connections (" + str(self.max_clients) + " max)...")

        self.__receive_loop()

    def stop(self):
        for client in self.clients:
            client.stop()
        self.connection.close()


def init():
    database = Database("test.db")
    server = Server(database, "localhost", 8888, 5)

    try:
        server.run()
    finally:
        server.stop()
        database.close()


if __name__ == "__main__":
    init()
