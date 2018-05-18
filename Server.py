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
        data = self.c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

        if data is None:
            self.__create_table_users()
            self.__create_table_channels()
        else:
            if ("users",) not in data:
                self.__create_table_users()
            if ("channels",) not in data:
                self.__create_table_channels()

        self.connection.commit()

    def __create_table_users(self):
        asd = "CREATE TABLE users (date TEXT, username TEXT, nick TEXT, password TEXT, rank INT, mute INT, ban INT)"
        self.c.execute(asd)

        data = [
            ("-", "root", "root", "123", 0, 0, 0),
            ("-", "1", "1", "1", 99, 0, 0),
            ("-", "2", "2", "2", 80, 0, 0),
            ("-", "3", "3", "3", 99, 1, 0),
            ("-", "4", "4", "4", 99, 1, 1)
        ]
        self.c.executemany("INSERT INTO users VALUES (?,?,?,?,?,?,?)", data)

    def __create_table_channels(self):
        self.c.execute("CREATE TABLE channels (name TEXT, max INT, rank INT)")

        # Add default channels
        data = [
            ("default", 512, 99),
            ("off-topic", 128, 90),
            ("music", 128, 20),
            ("code club", 64, 20),
            ("admin", 16, 10)
        ]

        self.c.executemany("INSERT INTO channels VALUES (?,?,?)", data)

    # ======================================================================================================
    # Entry creation
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

    # ======================================================================================================
    # Channel management
    # ======================================================================================================

    def list_channels(self):
        rows = self.c.execute("SELECT * FROM channels")
        return rows.fetchall()


class Channel:
    def __init__(self, channel_data):
        self.name = channel_data[0]
        self.max = int(channel_data[1])
        self.rank = int(channel_data[2])

        self.clients = []

    def to_csv(self):
        return "{0}:{1}:{2}:{3}".format(
            self.name,
            len(self.clients),
            self.max,
            self.rank
        )


class Client:
    def __init__(self, server, connection, address):
        self.server = server
        self.connection = connection
        self.address = address
        self.client_id = None
        self.thread = None

        self.logged_in = False

        self.channel = None
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
                data = self.connection.recv(MAX_MSG_LENGTH).decode("utf-8")
                print("[RAW - RECEIVE]", data)
                self.__parse_data(data)
        except ConnectionResetError:
            pass
        finally:
            self.stop()

    def __parse_data(self, data):
        split_data = data.split(" ", 1)
        cmd = split_data[0]
        content = split_data[1] if len(split_data) > 1 else ""

        if not self.logged_in:
            if cmd == "!login":
                self.__login(content)
            elif cmd == "!register":
                self.__register(content)
            return

        if cmd == "!msg":
            self.__form_message(content)

        elif cmd == "!channels":
            self.__cmd_channels()

        if cmd != "!msg":
            print("[RAW - RECEIVE] '{0}' sent command '{1}' with data '{2}'".format(self.username, cmd, content))

    def __form_message(self, msg):
        print("[MSG] {0} ({1}) ({2}:{3}): '{4}'".format(
            self.username,
            self.nick,
            self.address[0],
            self.address[1],
            msg
        ))

        self.server.send_msg_from_client_to_all_in_channel(self, msg)

    def __login(self, content):
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

        self.__join_default_channel()

        print("[LOGIN] '{0}' just logged in as client {1} from '{2}:{3}'".format(
            self.username,
            self.client_id,
            self.address[0],
            self.address[1]
        ))

    def __register(self, content):
        try:
            username = content.split(" ")[0]
            password = content.split(" ")[1]
        except IndexError:
            self.send_data("!error", "invalid info provided")
            return

        if not self.server.database.create_user(username, password):
            self.send_data("!error", "username already in use")
            return

        self.send_data("!success", "account created and logged in")
        self.logged_in = True

        self.username = username
        self.nick = username
        self.rank = 99
        self.mute = 0

    def __join_default_channel(self):
        self.channel = self.server.channels["default"]
        self.channel.clients.append(self)

    def __cmd_channels(self):
        reply = ""

        for name, channel in self.server.channels.items():
            if channel.rank >= self.rank:
                reply += channel.to_csv() + ","

        if reply.endswith(","):
            reply = reply[:len(reply) - 1]

        self.send_data("!channels", reply)

    # ======================================================================================================
    # Send data
    # ======================================================================================================

    def send_data(self, cmd, content):
        payload = cmd + " " + content

        print("[RAW - SEND]", payload)

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
        print("[DISCONNECT] '{0}' disconnected as client {1} from '{2}:{3}'".format(
            self.username,
            self.client_id,
            self.address[0],
            self.address[1]
        ))

        if self.connection:
            self.connection.close()

        self.server.clients.remove(self)
        self.channel.clients.remove(self)

    # ======================================================================================================
    # Utility functions
    # ======================================================================================================


class Server:
    def __init__(self, database, ip, port, max_clients):
        self.ip = ip
        self.port = port
        self.max_clients = max_clients
        self.clients = []
        self.channels = {}

        self.database = database
        self.connection = None

    # ======================================================================================================
    # Receive and process clients
    # ======================================================================================================

    def __loop_receive(self):
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
            if client != sender and client.channel == sender.channel:
                client.send_data(cmd, content)

    def send_msg_from_client_to_all_in_channel(self, sender, content):
        for client in self.channels[sender.channel.name].clients:
            if client != sender:
                client.send_data("!msg", content)

    # ======================================================================================================
    # Control functions
    # ======================================================================================================

    def __load_channels(self):
        print("Loaded channels:")
        for channel_data in self.database.list_channels():
            print("    {:12} - 0/{:<3} slots (rank <= {:2})".format(channel_data[0], channel_data[1], channel_data[2]))
            self.channels[channel_data[0]] = Channel(channel_data)

    def run(self):
        self.__load_channels()

        print("Starting server on '{0}:{1}'".format(self.ip, self.port))

        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.bind((self.ip, self.port))

        # Specifying max connections here doesn't really seem to work for some reason
        self.connection.listen(self.max_clients)

        print("Awaiting connections ({} max)...".format(self.max_clients))

        self.__loop_receive()

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
