from threading import Thread
import socket


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
                data = self.connection.recv(MAX_MSG_LENGTH).decode("utf-8")

                if data == "exit":
                    self.send_data("exit")
                    break

                print("Client {0} ({1}:{2}): '{3}'".format(self.client_id, self.address[0], self.address[1], data))
                self.server.message_all_but_sender("Client {0}> {1}".format(self.client_id, data), self)
        except ConnectionResetError:
            pass
        finally:
            self.stop()

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
        self.server.message_all_but_sender(msg, self)
        print(msg)

        self.connection.close()
        self.server.clients.remove(self)

    def send_data(self, data):
        try:
            self.connection.send(data.encode("utf-8"))
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
            self.message_all_but_sender(msg, client)
            print(msg)

    def _check_server_full(self, client):
        if len(self.clients) >= self.max_clients:
            client.send_data("full")
            client.connection.detach()

            msg = "Client (" + client.address[0] + ":" + str(client.address[1]) + ") couldn't connect (server full)"
            self.message_all(msg)
            print(msg)
            return True
        else:
            client.send_data("welcome")
            return False

    def message_all(self, msg):
        for client in self.clients:
            client.send_data(msg)

    def message_all_but_sender(self, msg, sender):
        for client in self.clients:
            if client != sender:
                client.send_data(msg)

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
