from threading import Thread
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


class Client:
    def __init__(self, server, connection, address):
        self.server = server
        self.connection = connection
        self.address = address
        self.client_id = None
        self.thread = None

    def __receive_loop(self):
        try:
            while True:
                self._process_data(self.connection.recv(MAX_MSG_LENGTH))
        except ConnectionResetError:
            pass
        finally:
            self.stop()

    def _process_data(self, data):
        data = data.decode("utf-8").split("::")

        header = data[0]
        body = data[1]

        if header == "bye":
            self.send_data("bye", "")
            return
        elif header == "message":
            print("Client {0} ({1}:{2}): '{3}'".format(self.client_id, self.address[0], self.address[1], body))
            self.server.send_data_to_all(self, "message", "Client {0}> {1}".format(self.client_id, body))

    def start(self, client_id):
        self.client_id = client_id

        self.thread = Thread(
            target=self.__receive_loop,
            name="client-" + str(self.client_id),
            daemon=True
        )

        self.thread.start()

    def stop(self):
        msg = "Client {0} ({1}:{2}) disconnected".format(self.client_id, self.address[0], self.address[1])
        self.server.send_data_to_all(self, "disconnect", msg)
        print(msg)

        self.connection.close()
        self.server.clients.remove(self)

    def send_data(self, header, body):
        payload = header + "::" + body

        try:
            self.connection.send(payload.encode("utf-8"))
        except ConnectionResetError:
            pass


class Server:
    def __init__(self, ip, port, max_clients):
        self.ip = ip
        self.port = port
        self.max_clients = max_clients
        self.clients = []

        self.connection = None

    def __receive_loop(self):
        while True:
            connection, address = self.connection.accept()
            client = Client(self, connection, address)

            skip = self._check_server_full(client)
            if skip: continue

            self.clients.append(client)
            client_id = self.clients.index(client)
            client.start(client_id)

            msg = "Client {0} ({1}:{2}) connected".format(client_id, address[0], address[1])
            self.send_data_to_all(client, "connected", msg)
            print(msg)

    def _check_server_full(self, client):
        if len(self.clients) >= self.max_clients:
            client.send_data("full")
            client.connection.detach()

            msg = "Client (" + client.address[0] + ":" + str(client.address[1]) + ") couldn't connect (server full)"
            self.send_data_to_all(client, "couldn't connect", msg)
            print(msg)
            return True
        else:
            client.send_data("welcome", "")
            return False

    def send_data_to_all(self, sender, header, body):
        for client in self.clients:
            if client != sender:
                client.send_data(header, body)

    def start(self):
        print("Starting server on '" + self.ip + "':'" + str(self.port) + "'")

        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.bind((self.ip, self.port))

        # Specifying max connections here doesn't really seem to work for some reason
        self.connection.listen(self.max_clients)

        print("Awaiting connections (" + str(self.max_clients) + " max)...")

        self.__receive_loop()

    def stop(self):
        for client in self.clients:
            client.send_data("exit")
            client.stop()
        self.connection.close()


def init():
    server = Server("localhost", 8888, 5)

    try:
        server.start()
    finally:
        server.stop()


if __name__ == "__main__":
    init()
