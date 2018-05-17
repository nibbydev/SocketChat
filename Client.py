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

    def _connect(self, data):
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
                data = self.connection.recv(MAX_MSG_LENGTH).decode("utf-8").split(" ", 1)

                self._sort_data(data[0], data[1])

        except ConnectionResetError:
            print("Server unexpectedly closed")
        except ConnectionAbortedError:
            print("Connection closed")

    def _sort_data(self, cmd, content):
        if not self.is_logged_in:
            self._process_login(cmd, content)
            return

        if cmd == "!msg":
            print(content)

    def _process_login(self, cmd, content):
        if cmd == "!login":
            print("[LOGIN]", content)
        elif cmd == "!error":
            print("[ERROR]", content)
            return
        elif cmd == "!success":
            print("[SUCC]", content)
            self.is_logged_in = True
            return

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
        try:
            while True:
                data = input()
                self._parse_command(data)
        except KeyboardInterrupt:
            self.exit()

    def _parse_command(self, data):
        if self.is_connected:
            if data.startswith("!disconnect"):
                self.disconnect()
                return

            if self.is_logged_in:
                if data.startswith("!kick"):
                    print("not implemented")
                else:
                    self.send_manual("!msg " + data)
            else:
                if data.startswith("!login"):
                    self.send_manual(data)
                elif data.startswith("!register"):
                    self.send_manual(data)
        else:
            if data.startswith("!connect"):
                self._connect(data)


def init():
    client = Client()
    client.run()


if __name__ == "__main__":
    init()
