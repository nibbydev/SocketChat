from threading import Thread
from time import sleep
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


MAX_MSG_LENGTH = 4096


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
            if ("permissions",) not in data:
                self.__create_table_permissions()

        self.connection.commit()

    def __create_table_users(self):
        asd = "CREATE TABLE users (date TEXT, username TEXT, nick TEXT, password TEXT, rank INT, mute INT, ban INT)"
        self.c.execute(asd)

        data = [
            ("-", "root", "root", "123", 0, 0, 0),
            ("-", "1", "1", "1", 99, 0, 0),
            ("-", "2", "2", "2", 80, 0, 0),
            ("-", "3", "3", "3", 99, 1, 0),
            ("-", "4", "4", "4", 99, 1, 1),
            ("-", "5", "5", "5", 4, 0, 0)
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

    def __create_table_permissions(self):
        self.c.execute("CREATE TABLE permissions (rank INT, name TEXT, mute INT, kick INT, ban INT, join_full INT, change_nick INT)")

        # Add default channels
        data = [
            (0, "owner", 1, 1, 1, 1, 1),
            (5, "admin", 1, 1, 1, 1, 1),
            (10, "mod", 1, 1, 0, 1, 1),
            (80, "member", 0, 0, 0, 0, 1),
            (99, "default", 0, 0, 0, 0, 0)
        ]

        self.c.executemany("INSERT INTO permissions VALUES (?,?,?,?,?,?,?)", data)

    # ======================================================================================================
    # Entry checking
    # ======================================================================================================

    def check_username_exists(self, username):
        row = self.c.execute("SELECT * FROM users WHERE username=?", (username,))
        entry = row.fetchone()

        return entry is not None

    def check_channel_exists(self, channel):
        row = self.c.execute("SELECT * FROM channels WHERE name=?", (channel,))
        entry = row.fetchone()

        return entry is not None

    def check_login(self, username, password):
        row = self.c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        return row.fetchone()

    # ======================================================================================================
    # Entry creation
    # ======================================================================================================

    def create_user(self, username, password):
        if self.check_username_exists(username):
            return False

        try:
            data = ("today", username, username, password, 99, 0, 0)
            self.c.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?)", data)
            self.connection.commit()
        except Exception as ex:
            print(ex)
            return False
        else:
            return True

    def create_channel(self, name, user_limit, rank):
        if self.check_channel_exists(name):
            return False

        try:
            data = (name, user_limit, rank)
            self.c.execute("INSERT INTO users VALUES (?,?,?)", data)
            self.connection.commit()
        except Exception as ex:
            print(ex)
            return False
        else:
            return True

    # ======================================================================================================
    # Entry removal
    # ======================================================================================================

    def remove_channel(self, channel):
        try:
            self.c.execute("DELETE FROM channels WHERE name=?", (channel,))
        except Exception as ex:
            print(ex)
            return False
        else:
            return True

    def remove_user(self, user):
        try:
            self.c.execute("DELETE FROM users WHERE username=?", (user,))
        except Exception as ex:
            print(ex)
            return False
        else:
            return True

    # ======================================================================================================
    # Entry updating
    # ======================================================================================================

    def mute_user(self, username, mute):
        try:
            self.c.execute("UPDATE users SET mute=? WHERE username =?", (mute, username))
            self.connection.commit()
        except Exception as ex:
            print(ex)
            return False
        else:
            return True

    def ban_user(self, username, ban):
        try:
            self.c.execute("UPDATE users SET ban=? WHERE username =?", (ban, username))
            self.connection.commit()
        except Exception as ex:
            print(ex)
            return False
        else:
            return True

    # ======================================================================================================
    # Entry listing
    # ======================================================================================================

    def list_channels(self):
        rows = self.c.execute("SELECT * FROM channels")
        return rows.fetchall()

    def list_permissions(self):
        rows = self.c.execute("SELECT * FROM permissions")
        return rows.fetchall()

    def get_user_data(self, username):
        return self.c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()


class Channel:
    def __init__(self, data):
        self.name = data[0]
        self.max = int(data[1])
        self.rank = int(data[2])

        self.clients = []

    def to_csv(self):
        client_csv = ""
        for client in self.clients:
            client_csv += "[{}] {}:".format(client.permission.name, client.username)

        if client_csv.endswith(";"):
            client_csv = client_csv[:len(client_csv) - 1]

        return "{}:{}:{}:{}:{}".format(self.name, len(self.clients), self.max, self.rank, client_csv)


class Permission:
    def __init__(self, data):
        self.rank = int(data[0])
        self.name = data[1]

        self.mute = True if data[2] == 1 else False
        self.kick = True if data[3] == 1 else False
        self.ban = True if data[4] == 1 else False
        self.join = True if data[5] == 1 else False
        self.nick = True if data[6] == 1 else False

        self.clients = []


class Client:
    def __init__(self, server, connection, address):
        self.server = server
        self.connection = connection
        self.address = address
        self.client_id = None
        self.thread = None

        self.logged_in = False

        self.channel = None
        self.permission = None

        self.username = None
        self.nick = None
        self.mute = False

    # ======================================================================================================
    # Receive and process messages
    # ======================================================================================================

    def __loop_receive(self):
        self.__cmd_help_login()
        sleep(0.1)
        self.send_data("!login", "")

        try:
            while True:
                sleep(0.1)
                data = self.connection.recv(MAX_MSG_LENGTH).decode("utf-8")
                # print("[RAW - RECEIVE]", data)
                self.__parse_data(data)
        except ConnectionResetError:
            pass
        except ConnectionAbortedError:
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
        elif cmd == "!mute":
            self.__cmd_mute(content)
        elif cmd == "!kick":
            self.__cmd_kick(content)
        elif cmd == "!ban":
            self.__cmd_ban(content)
        elif cmd == "!motd":
            self.__cmd_help_motd()
        elif cmd == "!help":
            self.__cmd_help_commands()
        else:
            self.send_data("!error", "server got unknown command: '{} {}'".format(cmd, content))

    def __form_message(self, msg):
        if self.mute:
            self.send_data("!mute", "you are muted")
            return

        print("[MSG][{}] {} ({}:{}): '{}'".format(
            self.permission.name,
            self.username,
            self.address[0],
            self.address[1],
            msg
        ))

        formatted_msg = "[{}][{}] {}: {}".format(self.channel.name, self.permission.name, self.username, msg)

        self.server.send_msg_from_client_to_all_in_channel(self, formatted_msg)

    # ----------------------------
    # Login or registration
    # ----------------------------

    def __login(self, content):
        try:
            username = content.split(" ")[0]
            password = content.split(" ")[1]
        except IndexError:
            self.send_data("!error", "invalid info provided")
            return

        user_data = self.server.database.check_login(username, password)

        if user_data is None:
            self.send_data("!error", "invalid username or password")
            return
        elif user_data[6] is 1:
            self.send_data("!error", "you are banned")
            return

        self.logged_in = True
        self.username = user_data[1]
        self.nick = user_data[2]
        self.mute = user_data[5]

        self.__disconnect_if_already_logged_in()

        self.__join_default_channel()
        self.__load_permissions(user_data[4])
        self.__welcome()

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

        self.logged_in = True
        self.username = username

        self.__join_default_channel()
        self.__load_permissions("99")
        self.__welcome()

        print("[REGISTER] '{0}' just registered as client {1} from '{2}:{3}'".format(
            self.username,
            self.client_id,
            self.address[0],
            self.address[1]
        ))

    def __disconnect_if_already_logged_in(self):
        for client in self.server.clients:
            if client is not self and client.username is self.username:
                client.send_data("!kick", "you logged in from another location")
                client.stop()
                break

    # ----------------------------
    # After login or registration
    # ----------------------------

    def __join_default_channel(self):
        self.channel = self.server.channels["default"]
        self.channel.clients.append(self)

    def __load_permissions(self, user_rank):
        for rank, permission in self.server.permissions.items():
            if int(user_rank) <= int(rank):
                self.permission = permission
                break

        self.permission.clients.append(self)

    def __welcome(self):
        self.send_data("!success", "logged in as '{}' with rank '{}' in channel '{}'".format(
            self.username, self.permission.name, self.channel.name
        ))

        sleep(0.1)

        self.__cmd_help_motd()

    # ======================================================================================================
    # Commands
    # ======================================================================================================

    def __cmd_channels(self):
        reply = ""

        for name, channel in self.server.channels.items():
            if channel.rank >= self.permission.rank:
                reply += channel.to_csv() + ","

        if reply.endswith(","):
            reply = reply[:len(reply) - 1]

        self.send_data("!channels", reply)

    def __cmd_mute(self, target):
        if not self.permission.mute:
            self.send_data("!error", "not enough permissions")
            return
        elif not target:
            self.send_data("!error", "no target")
            return

        target_data = self.server.database.get_user_data(target)

        if not target_data:
            self.send_data("!error", "no user by that username")
            return

        if target_data[4] <= self.permission.rank:
            self.send_data("!error", "the user has bigger or equal rank than you")
            return

        was_muted = target_data[5]
        self.server.database.mute_user(target, 1 - was_muted)

        print("[MUTE] {} {} {}".format(
            self.username,
            "unmuted" if was_muted else "muted",
            target
        ))

        self.send_data("!success", "user {} was {}".format(target, "unmuted" if was_muted else "muted"))

        for client in self.server.clients:
            if target == client.username:
                client.send_data("!mute", "you have been muted")
                client.mute = True

    def __cmd_ban(self, target):
        if not self.permission.ban:
            self.send_data("!error", "not enough permissions")
            return
        elif not target:
            self.send_data("!error", "no target")
            return

        target_data = self.server.database.get_user_data(target)

        if not target_data:
            self.send_data("!error", "no user by that username")
            return

        if target_data[4] <= self.permission.rank:
            self.send_data("!error", "the user has bigger or equal rank than you")
            return

        was_banned = target_data[6]
        self.server.database.ban_user(target, 1 - was_banned)

        print("[BAN] {} {} {}".format(
            self.username,
            "unbanned" if was_banned else "banned",
            target
        ))

        self.send_data("!success", "user {} was {}".format(target, "unbanned" if was_banned else "banned"))

        for client in self.server.clients:
            if target == client.username:
                client.send_data("!ban", "you have been banned")
                client.stop()

    def __cmd_kick(self, target):
        if not self.permission.kick:
            self.send_data("!error", "not enough permissions")
            return
        elif not target:
            self.send_data("!error", "no target")
            return

        for client in self.server.clients:
            if target == client.username:
                if client.permission.rank <= self.permission.rank:
                    self.send_data("!error", "the user has bigger or equal rank than you")
                    return

                print("[KICK] {} {} {}".format(self.username, "kicked", target))
                self.send_data("!success", "user {} was kicked".format(target))
                client.send_data("!kick", "you have been kicked")

                client.stop()
                return

        self.send_data("!error", "no user by that username")
        return

    # ----------------------------
    # Help pages
    # ----------------------------

    def __cmd_help_motd(self):
        help_string = """
===========================================================
| Welcome, {user}, to the {ip}:{port} server!
| Get started with !help
===========================================================
        """.strip().format(user=self.username, ip=self.server.ip, port=self.server.port)

        self.send_data("!box", help_string)

    def __cmd_help_commands(self):
        help_string = """
========================================
| User commands are:                   |
|   * !help - shows this page          |
|   * !channels - lists all available  |
|      channels and the users in them  |
|   * !channel <name> - join a channel |
| Admin commands are:                  |
|   * !mute <username> - toggle mute   |
|   * !kick <username> - kick user     |
|   * !ban <username> - toggle ban     |
========================================
        """.strip()

        self.send_data("!box", help_string)

    def __cmd_help_login(self):
        help_string = """
=========================================
| Usable commands are:                  |
|     * !login <username> <password>    |
|     * !register <username> <password> |
=========================================
        """.strip()

        self.send_data("!box", help_string)

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
        if not self.connection:
            return

        self.connection.close()
        self.connection = None

        print("[DISCONNECT] '{}' disconnected from '{}:{}'".format(
            self.username,
            self.address[0],
            self.address[1]
        ))

        try:
            self.server.clients.remove(self)
        except ValueError:
            pass

        try:
            self.channel.clients.remove(self)
        except ValueError:
            pass

        try:
            self.permission.clients.remove(self)
        except ValueError:
            pass


class Server:
    def __init__(self, database, ip, port, max_clients):
        self.ip = ip
        self.port = port
        self.max_clients = max_clients
        self.clients = []
        self.channels = {}
        self.permissions = {}

        self.database = database
        self.connection = None

    # ======================================================================================================
    # Receive and process clients
    # ======================================================================================================

    def __loop_receive(self):
        while True:
            sleep(0.1)
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
    # Load data from database on program start
    # ======================================================================================================

    def __load_channels(self):
        print("Loaded channels:")
        print("|   {:>12} | {:>5} | {:>4} |".format(
            "name", "slots", "rank"
        ))

        for data in self.database.list_channels():
            print("|   {:>12} | {:>5} | {:>4} |".format(
                data[0], data[1], data[2]
            ))
            self.channels[data[0]] = Channel(data)

        print()

    def __load_permissions(self):
        print("Loaded permissions:")
        print("|   {:>4} | {:>12} | {:>4} | {:>4} | {:>3} | {:>9} | {:>11} |".format(
            "rank", "name", "mute", "kick", "ban", "join full", "change nick"
        ))

        for data in self.database.list_permissions():
            print("|   {:>4} | {:>12} | {:>4} | {:>4} | {:>3} | {:>9} | {:>11} |".format(
                data[0], data[1], data[2], data[3], data[4], data[5], data[6]
            ))

            self.permissions[data[0]] = Permission(data)

        print()

    # ======================================================================================================
    # Control functions
    # ======================================================================================================

    def run(self):
        self.__load_channels()
        self.__load_permissions()

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
