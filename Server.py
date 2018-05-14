from threading import Thread
import socket


HOST = 'localhost'
PORT = 8888
MAX_CONNECTIONS = 5
ACTIVE_CONNECTIONS = []
MAX_LENGTH = 2056


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
                data = self.connection.recv(MAX_LENGTH)
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
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((HOST, PORT))
    except socket.error:
        return 1

    s.listen(MAX_CONNECTIONS)

    print("Awaiting connections ("+str(MAX_CONNECTIONS)+" max)...")

    try:
        while True:
            conn, address = s.accept()
            conn_obj = Connection(conn, address)

            reply = "Client "+str(len(ACTIVE_CONNECTIONS))+" ("+address[0]+":"+str(address[1])+") connected"
            print(reply)
            for connection in ACTIVE_CONNECTIONS:
                connection.send_data(reply)

            ACTIVE_CONNECTIONS.append(conn_obj)
            conn_obj.start()

    finally:
        for connection in ACTIVE_CONNECTIONS:
            connection.send_data("exit")
            connection.stop()
        s.close()


if __name__ == "__main__":
    init()
