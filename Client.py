from threading import Thread
import socket


MAX_MSG_LENGTH = 16

DEV_USERNAME = "5"
DEV_PASSWORD = "5"


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
==================================
| Usable commands are:           |
|     * !connect <ip> <port>     |
==================================
        """.strip()

        print(help_string)

    # ======================================================================================================
    # Receive and process messages
    # ======================================================================================================

    def __loop_receive(self):
        try:
            buffer = bytearray()

            while True:
                buffer += self.connection.recv(MAX_MSG_LENGTH)

                length_as_string = buffer.decode("utf-8").split(" ", 1)[0]
                length_of_length = len(length_as_string) + 1
                length = int(length_as_string) + length_of_length

                while len(buffer) < length:
                    buffer += self.connection.recv(MAX_MSG_LENGTH)

                data = buffer[length_of_length:length]
                buffer = buffer[length:]

                data = data.decode("utf-8").split(" ", 1)
                self.__parse_received_data(data[0], data[1])
        except ConnectionResetError:
            print("Server unexpectedly closed")
        except ConnectionAbortedError:
            print("Connection closed")
        finally:
            self.disconnect()
            self.__help()

    def __parse_received_data(self, cmd, content):
        if cmd == "!box":
            print(content)
            return

        if not self.is_logged_in:
            if cmd == "!success":
                print("[SUCCESS]", content)
                self.is_logged_in = True
                return

            # TODO: remove this
            # self.send_data("!login " + DEV_USERNAME + " " + DEV_PASSWORD)

        if cmd == "!error":
            print("[ERROR]", content)
        elif cmd == "!success":
            print("[SUCCESS]", content)
        elif cmd == "!log":
            print(content)
        elif cmd == "!msg":
            print(content)
        elif cmd == "!channels":
            self.__parse_channels(content)
        elif cmd == "!permissions":
            self.__parse_permissions(content)
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

    def __parse_channels(self, data):
        print("[CHANNELS] Channels and users in the server:")

        for channel_data in data.split(","):
            data = channel_data.split(":")

            print(" |- {:12} {:>3}/{:<3} slots (rank <= {:2})".format(data[0], data[1], data[2], data[3]))

            if data[4]:
                for client in data[4].split(";"):
                    print(" |  {}".format(client))

    def __parse_permissions(self, data):
        print("[Permissions] Permissions in the server:")

        print("| {:>2} | {:>4} | {:>12} | {:>4} | {:>4} | {:>3} | {:>9} | {:>11} |".format(
            "id", "rank", "name", "mute", "kick", "ban", "join full", "change nick"
        ))

        for perm_data in data.split(","):
            data = perm_data.split(":")

            print("| {:>2} | {:>4} | {:>12} | {:>4} | {:>4} | {:>3} | {:>9} | {:>11} |".format(
                data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7]
            ))

    # ======================================================================================================
    # Send data
    # ======================================================================================================

    def send_data(self, data):
        encoded = bytearray(data.encode("utf-8"))
        length_of_encoded = len(encoded)
        prefix = str(length_of_encoded) + " "
        encoded[0:0] = prefix.encode("utf-8")

        try:
            self.connection.sendall(encoded)
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
