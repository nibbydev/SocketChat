from threading import Thread
import socket


MAX_MSG_LENGTH = 2056


class Client:
    def __init__(self):
        self.connection = None
        self.receive_thread = None

        self.is_logged_in = False
        self.is_connected = False

        self.username = "myUsername"
        self.password = "myPassword"

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

    # ======================================================================================================
    # Receive and process messages
    # ======================================================================================================

    def __loop_receive(self):
        try:
            while True:
                data = self.connection.recv(MAX_MSG_LENGTH).decode("utf-8")
                print("[RAW]", data)

                data = data.split(" ", 1)
                self.__parse_received_data(data[0], data[1])

        except ConnectionResetError:
            print("Server unexpectedly closed")
        except ConnectionAbortedError:
            print("Connection closed")

    def __parse_received_data(self, cmd, content):
        if not self.is_logged_in:
            self.__process_login(cmd, content)
            return

        if cmd == "!msg":
            print(content)
        elif cmd == "!channels":
            self.__parse_channels(content)

    def __process_login(self, cmd, content):
        if cmd == "!login":
            print("[LOGIN]", content)
            # TODO: remove
            self.send_manual("!login 2 2")
        elif cmd == "!error":
            print("[ERROR]", content)
            return
        elif cmd == "!success":
            print("[SUCC]", content)
            self.is_logged_in = True
            return

    def __parse_channels(self, data):
        channels = data.split(",")
        print("Channels in the server:")

        for channel_data in channels:
            split_channel_data = channel_data.split(":")

            print("    '{:12}' {:>3}/{:<3} slots (accessible to rank <= {:2})".format(
                split_channel_data[0],
                split_channel_data[1],
                split_channel_data[2],
                split_channel_data[3]
            ))

    # ======================================================================================================
    # Send data
    # ======================================================================================================

    def send_manual(self, data):
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
                    self.send_manual(data)
                else:
                    self.send_manual("!msg " + data)
                    print("!msg " + data)
                    print("!msg " + data)
            else:
                if data.startswith("!login"):
                    self.send_manual(data)
                elif data.startswith("!register"):
                    self.send_manual(data)
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
