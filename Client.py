from threading import Thread
from time import sleep
import socket


MAX_MSG_LENGTH = 2056

DEV_USERNAME = "2"
DEV_PASSWORD = "2"


class Client:
    def __init__(self):
        self.connection = None
        self.receive_thread = None

        self.is_logged_in = False
        self.is_connected = False

        self.username = "myUsername"
        self.password = "myPassword"

        self.__help()

    # ======================================================================================================
    # User commands
    # ======================================================================================================

    def __connect(self, data):
        ip = data.split(" ")[1]
        port = int(data.split(" ")[2])

        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.connect((ip, port))

        self.receive_thread = Thread(target=self.__loop_receive, daemon=True)
        self.receive_thread.start()

        self.is_connected = True

    def disconnect(self):
        if not self.is_connected:
            print("No active connections")
            return

        self.connection.close()

        self.connection = None
        self.receive_thread = None

        self.is_connected = False
        self.is_logged_in = False

    def __help(self):
        help_string = """
    Welcome, to the chat application!
    Generic commands are:
        * !connect <ip> <port>
    Once connected, you can use:
        * !login <username> <password>
        * !register <username> <password>
        """.strip()

        print(help_string)

    # ======================================================================================================
    # Receive and process messages
    # ======================================================================================================

    def __loop_receive(self):
        try:
            while True:
                sleep(0.1)
                data = self.connection.recv(MAX_MSG_LENGTH).decode("utf-8")
                # print("[RAW - RECEIVE]", data)

                data = data.split(" ", 1)
                self.__parse_received_data(data[0], data[1])

        except ConnectionResetError:
            print("Server unexpectedly closed")
        except ConnectionAbortedError:
            print("Connection closed")
        finally:
            self.disconnect()

    def __parse_received_data(self, cmd, content):
        if not self.is_logged_in:
            self.__process_login(cmd, content)
            return

        if cmd == "!error":
            print("[ERROR]", content)
        elif cmd == "!success":
            print("[SUCCESS]", content)
        elif cmd == "!msg":
            print(content)
        elif cmd == "!channels":
            self.__parse_channels(content)
        elif cmd == "!welcome":
            print("[WELCOME]", content)
        elif cmd == "!help":
            print("[HELP]", content)
        elif cmd == "!kick":
            print("[KICK]", content)
        elif cmd == "!ban":
            print("[BAN]", content)
        elif cmd == "!mute":
            print("[MUTE]", content)
        else:
            print("unknown server command: '{} {}'".format(cmd, content))

    def __process_login(self, cmd, content):
        if cmd == "!login":
            print("[LOGIN]", content)
            # TODO: remove
            self.send_data("!login " + DEV_USERNAME + " " + DEV_PASSWORD)
        elif cmd == "!error":
            print("[ERROR]", content)
            return
        elif cmd == "!success":
            print("[SUCCESS]", content)
            self.is_logged_in = True
            return

    def __parse_channels(self, data):
        channels = data.split(",")
        print("[CHANNELS] Channels and users in the server:")

        for channel_data in channels:
            data = channel_data.split(":")

            print(" *  {:12} {:>3}/{:<3} slots (rank <= {:2})".format(data[0], data[1], data[2], data[3]))

            if data[4]:
                for client in data[4].split(";"):
                    print("      * {}".format(client))

    # ======================================================================================================
    # Send data
    # ======================================================================================================

    def send_data(self, data):
        # print("[RAW - SEND]", data)

        try:
            self.connection.sendall(data.encode("utf-8"))
        except ConnectionResetError:
            pass

    # ======================================================================================================
    # Command loop
    # ======================================================================================================

    def run(self):
        # TODO: remove
        self.__parse_local_command("!connect localhost 8888")

        try:
            while True:
                sleep(0.1)
                data = input()
                self.__parse_local_command(data)
        except KeyboardInterrupt:
            self.disconnect()

    def __parse_local_command(self, data):
        if self.is_connected:
            if data.startswith("!disconnect"):
                self.disconnect()
                return

            if self.is_logged_in:
                if data.startswith("!"):
                    self.send_data(data)
                else:
                    self.send_data("!msg " + data)
            else:
                if data.startswith("!login"):
                    self.send_data(data)
                elif data.startswith("!register"):
                    self.send_data(data)
                else:
                    print("[ERROR] Unknown command:", data)
        else:
            if data.startswith("!connect"):
                self.__connect(data)


def init():
    client = Client()
    client.run()


if __name__ == "__main__":
    init()
