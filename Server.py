from threading import Thread
import socket


HOST = 'localhost'
PORT = 8888
MAX_CONNECTIONS = 5
ACTIVE_CONNECTIONS = []
MAX_MSG_LENGTH = 2056


class Connection(object):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        self.id = len(ACTIVE_CONNECTIONS)

        self.thread = Thread(
            target=self.main_loop,
            name="connection-" + str(self.id),
            daemon=True
        )

    def main_loop(self):
        try:
            while True:
                data = self.connection.recv(MAX_MSG_LENGTH)
                msg = data.decode("utf-8")

                print("Client "+str(self.id)+" ("+self.address[0]+":"+str(self.address[1])+"): '"+msg+"'")

                for connection in ACTIVE_CONNECTIONS:
                    if connection != self:
                        connection.send_data("Client "+str(self.id)+"> "+msg)

                if msg == "exit":
                    self.send_data("exit")
                    break
        except ConnectionResetError:
            pass
        finally:
            self.stop()

    def start(self):
        self.thread.start()

    def stop(self):
        reply = "Client "+str(self.id)+" ("+self.address[0]+":"+str(self.address[1])+") disconnected"
        print(reply)
        for connection in ACTIVE_CONNECTIONS:
            connection.send_data(reply)

        self.connection.close()
        ACTIVE_CONNECTIONS.remove(self)

    def send_data(self, data):
        try:
            self.connection.send(data.encode("utf-8"))
        except ConnectionResetError:
            pass


def init():
    print("Binding socket on '"+HOST+"':'"+str(PORT)+"'")

    try:
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.bind((HOST, PORT))
    except socket.error:
        return 1

    # Specifying max connections here doesn't really seem to work for some reason
    connection.listen(MAX_CONNECTIONS)

    print("Awaiting connections ("+str(MAX_CONNECTIONS)+" max)...")

    try:
        while True:
            connection_data, address = connection.accept()

            if len(ACTIVE_CONNECTIONS) >= MAX_CONNECTIONS:
                connection_data.send("full".encode("utf-8"))
                connection_data.detach()

                reply = "Client (" + address[0]+":"+str(address[1])+") couldn't connect (server full)"
                print(reply)
                for conn in ACTIVE_CONNECTIONS:
                    conn.send_data(reply)

                continue
            else:
                connection_data.send("welcome".encode("utf-8"))

            connection_object = Connection(connection_data, address)

            reply = "Client "+str(len(ACTIVE_CONNECTIONS))+" ("+address[0]+":"+str(address[1])+") connected"
            print(reply)
            for conn in ACTIVE_CONNECTIONS:
                conn.send_data(reply)

            ACTIVE_CONNECTIONS.append(connection_object)
            connection_object.start()

    finally:
        for conn in ACTIVE_CONNECTIONS:
            conn.send_data("exit")
            conn.stop()
        connection.close()


if __name__ == "__main__":
    init()
