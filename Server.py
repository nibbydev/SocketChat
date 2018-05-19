from threading import Thread
from re import match
import sqlite3
import socket


CHANNEL_LOG_LENGTH = 32

# This only have effect when the database is generated
ROOT_PASSWORD = "M83Kj5QGxWCh2YMG"


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
        self.c.execute(
            """CREATE TABLE users (
                    id INTEGER PRIMARY KEY, 
                    username TEXT UNIQUE NOT NULL, 
                    nick TEXT DEFAULT NULL, 
                    password TEXT NOT NULL, 
                    rank INT DEFAULT 99, 
                    muted INT DEFAULT 0, 
                    banned INT DEFAULT 0)"""
        )

        data = [
            ("root", ROOT_PASSWORD, 0)
        ]

        self.c.executemany("INSERT INTO users(username,password,rank) VALUES (?,?,?)", data)

    def __create_table_channels(self):
        self.c.execute(
            """CREATE TABLE channels (
                    id INTEGER PRIMARY KEY, 
                    name TEXT UNIQUE NOT NULL, 
                    max INT DEFAULT 64, 
                    rank INT DEFAULT 99)"""
        )

        # Add default channels
        data = [
            ("default",     512,    99),
            ("off-topic",   128,    90),
            ("admin",       16,     10)
        ]

        self.c.executemany("INSERT INTO channels(name,max,rank) VALUES (?,?,?)", data)

    def __create_table_permissions(self):
        self.c.execute(
            """CREATE TABLE permissions (
                    id INTEGER PRIMARY KEY, 
                    rank INT NOT NULL,
                    name TEXT UNIQUE NOT NULL, 
                    mute INT DEFAULT 0, 
                    kick INT DEFAULT 0, 
                    ban INT DEFAULT 0, 
                    join_full INT DEFAULT 0, 
                    change_nick INT DEFAULT 0)"""
        )

        # Add default channels
        data = [
            (0,     "owner",    1, 1, 1, 1, 1),
            (5,     "admin",    1, 1, 1, 1, 1),
            (10,    "mod",      1, 1, 0, 1, 1),
            (80,    "member",   0, 0, 0, 0, 1),
            (99,    "default",  0, 0, 0, 0, 0)
        ]

        self.c.executemany("""INSERT INTO permissions(rank,name,mute,kick,ban,join_full,change_nick) 
                              VALUES (?,?,?,?,?,?,?)""", data)

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
        try:
            self.c.execute("INSERT INTO users(username,password) VALUES (?,?)", (username, password))
            self.connection.commit()
        except Exception as ex:
            print(ex)
            self.connection.rollback()
            return False
        else:
            return True

    def create_channel(self, name, user_limit, rank):
        try:
            self.c.execute("INSERT INTO channels(name,max,rank) VALUES (?,?,?)", (name, user_limit, rank))
            self.connection.commit()
        except Exception as ex:
            print(ex)
            self.connection.rollback()
            return False
        else:
            return True

    def create_rank(self, rank, name, mute, kick, ban, full, nick):
        try:
            self.c.execute("""INSERT INTO permissions(rank,name,mute,kick,ban,join_full,change_nick) 
                                          VALUES (?,?,?,?,?,?,?)""", (rank, name, mute, kick, ban, full, nick))
            self.connection.commit()
        except Exception as ex:
            print(ex)
            self.connection.rollback()
            return False
        else:
            return True

    # ======================================================================================================
    # Entry removal
    # ======================================================================================================

    def remove_channel(self, channel):
        try:
            self.c.execute("DELETE FROM channels WHERE name=?", (channel,))
            self.connection.commit()
        except Exception as ex:
            print(ex)
            self.connection.rollback()
            return False
        else:
            return True

    def remove_user(self, user):
        try:
            self.c.execute("DELETE FROM users WHERE username=?", (user,))
            self.connection.commit()
        except Exception as ex:
            print(ex)
            self.connection.rollback()
            return False
        else:
            return True

    def remove_rank(self, name):
        try:
            self.c.execute("DELETE FROM permissions WHERE name=?", (name,))
            self.connection.commit()
        except Exception as ex:
            print(ex)
            self.connection.rollback()
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
            self.connection.rollback()
            return False
        else:
            return True

    def ban_user(self, username, ban):
        try:
            self.c.execute("UPDATE users SET ban=? WHERE username =?", (ban, username))
            self.connection.commit()
        except Exception as ex:
            print(ex)
            self.connection.rollback()
            return False
        else:
            return True

    def change_nick(self, username, new_name):
        try:
            self.c.execute("UPDATE users SET nick=? WHERE username =?", (new_name, username))
            self.connection.commit()
        except Exception as ex:
            print(ex)
            self.connection.rollback()
            return False
        else:
            return True

    # ======================================================================================================
    # Entry listing
    # ======================================================================================================

    def list_channels(self):
        return self.c.execute("SELECT * FROM channels").fetchall()

    def list_permissions(self):
        return self.c.execute("SELECT * FROM permissions").fetchall()

    def list_users(self):
        return self.c.execute("SELECT * FROM users").fetchall()

    def get_user_data(self, username):
        return self.c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()


class Channel:
    def __init__(self, data):
        self.id = data[0]
        self.name = data[1]
        self.max = data[2]
        self.rank = data[3]

        self.clients = []
        self.chat_log = []

    def to_csv(self):
        client_csv = ""
        for client in self.clients:
            client_csv += "[{}] {};".format(client.permission.name, client.username)

        if client_csv.endswith(";"):
            client_csv = client_csv[:len(client_csv) - 1]

        return "{}:{}:{}:{}:{}".format(self.name, len(self.clients), self.max, self.rank, client_csv)

    def log(self, msg):
        self.chat_log.append(msg)

        if len(self.chat_log) > CHANNEL_LOG_LENGTH:
            self.chat_log = self.chat_log[CHANNEL_LOG_LENGTH:]


class Permission:
    def __init__(self, data):
        self.id = data[0]
        self.rank = data[1]
        self.name = data[2]

        self.mute = True if data[3] == 1 else False
        self.kick = True if data[4] == 1 else False
        self.ban =  True if data[5] == 1 else False
        self.join = True if data[6] == 1 else False
        self.nick = True if data[7] == 1 else False

        self.clients = []

    def to_csv(self):
        return "{}:{}:{}:{}:{}:{}:{}:{}".format(
            self.id,
            self.rank,
            self.name,
            1 if self.mute else 0,
            1 if self.kick else 0,
            1 if self.ban else 0,
            1 if self.join else 0,
            1 if self.nick else 0
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
        self.permission = None

        self.username = None
        self.nick = None
        self.mute = False

    # ======================================================================================================
    # Receive and process messages
    # ======================================================================================================

    def __loop_receive(self):
        self.__cmd_help_login()

        try:
            buffer = bytearray()

            while True:
                buffer += self.connection.recv(16)

                length_as_string = buffer.decode("utf-8").split(" ", 1)[0]
                length_of_length = len(length_as_string) + 1
                length = int(length_as_string) + length_of_length

                while len(buffer) < length:
                    buffer += self.connection.recv(16)

                data = buffer[length_of_length:length]
                buffer = buffer[length:]

                self.__parse_data(data.decode("utf-8"))
        except ConnectionResetError:
            pass
        except ConnectionAbortedError:
            pass
        except UnicodeDecodeError:
            print("[KICK] disconnected '{}' ({}:{}) for sending invalid data".format(
                self.username,
                self.address[0],
                self.address[1]
            ))

            self.send_data("!kick", "you have been kicked")
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
            self.__cmd_list_channels()
        elif cmd == "!permissions":
            self.__cmd_list_permissions()
        elif cmd == "!rm_permission":
            self.__cmd_remove_permission(content)
        elif cmd == "!rm_user":
            self.__cmd_remove_user(content)
        elif cmd == "!rm_channel":
            self.__cmd_remove_channel(content)
        elif cmd == "!mk_permission":
            self.__cmd_create_permission(content)
        elif cmd == "!mk_channel":
            self.__cmd_create_channel(content)
        elif cmd == "!channel":
            self.__cmd_switch_channel(content)
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
        elif cmd == "!nick":
            self.__cmd_change_nick(content)
        else:
            self.send_data("!error", "server got unknown command: '{} {}'".format(cmd, content))

    def __form_message(self, msg):
        if self.mute:
            self.send_data("!mute", "you are muted")
            return

        print("[{channel}][{rank}] {username} ({ip}:{port}): '{msg}'".format(
            channel=self.channel.name,
            rank=self.permission.name,
            username=self.username,
            ip=self.address[0],
            port=self.address[1],
            msg=msg
        ))

        formatted_msg = "[{channel}][{rank}] {username}: {msg}".format(
            channel=self.channel.name,
            rank=self.permission.name,
            username=self.username if self.nick is None else self.nick,
            msg=msg
        )

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

        if not Client.check_if_contains_only_alphanumeric(username):
            self.send_data("!error", "illegal characters in username")
            return

        if len(username) > 16:
            self.send_data("!error", "username too long")
            return
        elif len(password) > 24:
            self.send_data("!error", "password too long")
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

        if not Client.check_if_contains_only_alphanumeric(username):
            self.send_data("!error", "illegal characters in username")
            return

        if len(username) > 16:
            self.send_data("!error", "username too long")
            return
        elif len(password) > 24:
            self.send_data("!error", "password too long")
            return

        if not self.server.database.create_user(username, password):
            self.send_data("!error", "username already in use")
            return

        self.logged_in = True
        self.username = username

        self.__join_default_channel()
        self.__load_permissions(99)
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
        for channel in self.server.channels:
            if channel.name == "default":
                self.channel = channel
                break

        self.channel.clients.append(self)

    def __load_permissions(self, user_rank):
        for permission in self.server.permissions:
            if user_rank <= permission.rank:
                self.permission = permission
                break

        self.permission.clients.append(self)

    def __welcome(self):
        self.__load_channel_chat_log()

        self.send_data("!success", "logged in as '{}' with rank '{}' in channel '{}'".format(
            self.username, self.permission.name, self.channel.name
        ))

        self.__cmd_help_motd()

    # ======================================================================================================
    # Commands
    # ======================================================================================================

    def __cmd_list_channels(self):
        reply = ""

        for channel in self.server.channels:
            if channel.rank >= self.permission.rank:
                reply += channel.to_csv() + ","

        if reply.endswith(","):
            reply = reply[:len(reply) - 1]

        self.send_data("!channels", reply)

    def __cmd_switch_channel(self, target):
        for channel in self.server.channels:
            if channel.name == target:
                if channel.rank < self.permission.rank:
                    self.send_data("!error", "not enough permissions to join '{}'".format(target))
                    return
                elif len(channel.clients) >= channel.max:
                    if not self.permission.join:
                        self.send_data("!error", "channel '{}' is full".format(target))
                        return

                self.channel.clients.remove(self)
                self.channel = channel
                self.channel.clients.append(self)

                self.__load_channel_chat_log()
                self.send_data("!success", "switched to channel '{}'".format(self.channel.name))
                return

        self.send_data("!error", "couldn't find channel '{}'".format(target))

    def __load_channel_chat_log(self):
        for msg in self.channel.chat_log:
            self.send_data("!log", msg)

    def __cmd_change_nick(self, new_name):
        if not self.permission.nick:
            self.send_data("!error", "not enough permissions")
            return

        if not Client.check_if_contains_only_alphanumeric(new_name):
            self.send_data("!error", "illegal characters in nickname")
            return

        if len(new_name) > 16:
            self.send_data("!error", "nickname too long")
            return

        new_name = None if new_name is "" else "*" + new_name

        self.server.database.change_nick(self.username, new_name)
        self.nick = new_name

        if new_name is None:
            print("[NICK] {} removed their nick".format(self.username))
            self.send_data("!success", "nick removed")
        else:
            print("[NICK] {} changed nick to '{}'".format(self.username, new_name))
            self.send_data("!success", "nick changed to '{}'".format(new_name))

    # ----------------------------
    # Admin commands
    # ----------------------------

    def __cmd_list_permissions(self):
        if self.permission.rank > 5:
            self.send_data("!error", "not enough permissions")
            return

        reply = ""

        for permission in self.server.permissions:
            reply += permission.to_csv() + ","

        if reply.endswith(","):
            reply = reply[:len(reply) - 1]

        self.send_data("!permissions", reply)

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

    def __cmd_remove_permission(self, target):
        if self.permission.rank > 0:
            self.send_data("!error", "not enough permissions")
            return

        if self.server.database.remove_rank(target):
            self.send_data("!success", "rank '{}' removed. applied after restart".format(target))
        else:
            self.send_data("!error", "couldn't remove rank '{}'".format(target))

    def __cmd_remove_user(self, target):
        if self.permission.rank > 0:
            self.send_data("!error", "not enough permissions")
            return

        if self.server.database.remove_user(target):
            self.send_data("!success", "user '{}' removed. applied after restart".format(target))
        else:
            self.send_data("!error", "couldn't remove user '{}'".format(target))

    def __cmd_remove_channel(self, target):
        if self.permission.rank > 0:
            self.send_data("!error", "not enough permissions")
            return

        if self.server.database.remove_channel(target):
            self.send_data("!success", "channel '{}' removed. applied after restart".format(target))
        else:
            self.send_data("!error", "couldn't remove channel '{}'".format(target))

    def __cmd_create_channel(self, data):
        if self.permission.rank > 0:
            self.send_data("!error", "not enough permissions")
            return

        try:
            name = data.split(" ")[0]
            limit = int(data.split(" ")[1])
            rank = int(data.split(" ")[2])
        except (ValueError, IndexError):
            self.send_data("!error", "invalid info provided")
            return

        if self.server.database.create_channel(name, limit, rank):
            reply = "channel '{}' (with {} slots for ranks {} or less) created. applied after restart".format(
                name, limit, rank
            )
            self.send_data("!success", reply)
        else:
            reply = "couldn't create channel '{}' (with {} slots for ranks {} or less) created".format(
                name, limit, rank
            )
            self.send_data("!error", reply)

    def __cmd_create_permission(self, data):
        if self.permission.rank > 0:
            self.send_data("!error", "not enough permissions")
            return

        try:
            rank = int(data.split(" ")[0])
            name = data.split(" ")[1]
            mute = int(data.split(" ")[2])
            kick = int(data.split(" ")[3])
            ban = int(data.split(" ")[4])
            full = int(data.split(" ")[5])
            nick = int(data.split(" ")[6])
        except (ValueError, IndexError):
            self.send_data("!error", "invalid info provided")
            return

        if mute != 0 and mute != 1:
            self.send_data("!error", "invalid mute value provided")
            return
        elif kick != 0 and kick != 1:
            self.send_data("!error", "invalid kick value provided")
            return
        elif ban != 0 and ban != 1:
            self.send_data("!error", "invalid ban value provided")
            return
        elif full != 0 and full != 1:
            self.send_data("!error", "invalid full value provided")
            return
        elif nick != 0 and nick != 1:
            self.send_data("!error", "invalid nick value provided")
            return

        if self.server.database.create_rank(rank, name, mute, kick, ban, full, nick):
            self.send_data("!success", "permission created. applied after restart")
        else:
            self.send_data("!error", "couldn't create permission")

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
===============================================
| User commands are:                          |
|   * !help - shows this page                 |
|   * !channels - lists all available         |
|      channels and the users in them         |
|   * !channel <name> - join a channel        |
| Restricted user commands are:               |
|   * !nick <name> - change nickname          |
|   * !nick - remove nickname                 |
| Admin commands are:                         |
|   * !mute <username> - toggle mute          |
|   * !kick <username> - kick user            |
|   * !ban <username> - toggle ban            |
|   * !permissions - list all ranks           |
| Owner commands are:                         |
|   * !rm_permission <name> delete permission |
|   * !rm_channel <name> - delete channel     |
|   * !rm_user <name> - delete user           | (It just won't fit)
|   * !mk_permission <rank: 0-99> <name> <mute: 1/0> <kick: 1/0> <ban: 1/0> <full: 1/0> <nick: 1/0>
|   * !mk_channel <name> <limit> <rank: 0-99> |
===============================================
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

        encoded = bytearray(payload.encode("utf-8"))
        length_of_encoded = len(encoded)
        prefix = str(length_of_encoded) + " "
        encoded[0:0] = prefix.encode("utf-8")

        try:
            self.connection.send(encoded)
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
        except (ValueError, AttributeError):
            pass

        try:
            self.channel.clients.remove(self)
        except (ValueError, AttributeError):
            pass

        try:
            self.permission.clients.remove(self)
        except (ValueError, AttributeError):
            pass

    # ======================================================================================================
    # Utility
    # ======================================================================================================

    @staticmethod
    def check_if_contains_only_alphanumeric(string):
        return match("^[\w_]+$", string) is not None


class Server:
    def __init__(self, database, ip, port, max_clients):
        self.ip = ip
        self.port = port
        self.max_clients = max_clients
        self.clients = []
        self.channels = []
        self.permissions = []

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
        sender.channel.log(content)

        for client in sender.channel.clients:
            if client is not sender:
                client.send_data("!msg", content)

    # ======================================================================================================
    # Load data from database on program start
    # ======================================================================================================

    def __load_channels(self):
        print("Loaded channels:")
        print("| {:>2} | {:>12} | {:>5} | {:>4} |".format("id", "name", "slots", "rank"))

        for data in self.database.list_channels():
            print("| {:>2} | {:>12} | {:>5} | {:>4} |".format(data[0], data[1], data[2], data[3]))
            self.channels.append(Channel(data))

        print()

    def __load_permissions(self):
        print("Loaded permissions:")
        print("| {:>2} | {:>4} | {:>12} | {:>4} | {:>4} | {:>3} | {:>9} | {:>11} |".format(
            "id", "rank", "name", "mute", "kick", "ban", "join full", "change nick"
        ))

        for data in self.database.list_permissions():
            print("| {:>2} | {:>4} | {:>12} | {:>4} | {:>4} | {:>3} | {:>9} | {:>11} |".format(
                data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7]
            ))

            self.permissions.append(Permission(data))

        print()

    def __list_users(self):
        print("Listing users:")
        print("| {:>2} | {:>16} | {:>16} | {:>16} | {:>4} | {:>5} | {:>6} |".format(
            "id", "username", "nick", "password", "rank", "muted", "banned"
        ))

        for data in self.database.list_users():
            print("| {:>2} | {:>16} | {:>16} | {:>16} | {:>4} | {:>5} | {:>6} |".format(
                data[0], data[1], str(data[2]), data[3], data[4], data[5], data[6]
            ))

        print()

    # ======================================================================================================
    # Control functions
    # ======================================================================================================

    def run(self):
        self.__load_channels()
        self.__load_permissions()
        self.__list_users()

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
    database = Database("data.db")
    server = Server(database, "localhost", 8888, 5)

    try:
        server.run()
    finally:
        server.stop()
        database.close()


if __name__ == "__main__":
    init()
