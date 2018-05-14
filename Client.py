import tkinter as tk
from tkinter import Text
from threading import Thread
import socket


HOST = 'localhost'
PORT = 8888
MAX_LENGTH = 2056


class MainWindow(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent

        self.__build_gui()

        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.connect((HOST, PORT))

        self.receive_thread = Thread(target=self.__loop_receive, daemon=True)
        self.receive_thread.start()

        self.console.insert(self.console.index('end'), "Connected\nTop windows shows messages, bottom window "
                                                       "sends messages.\nPress enter to send your message.\n")

    def __build_gui(self):
        self.root.title("Text Chat")
        self.root.option_add('*tearOff', 'FALSE')

        frame = tk.Frame(master=self.root)
        frame.pack(fill=tk.BOTH, expand=True)

        # Add text widget to display logging info
        self.console = Text(frame, height=10)
        self.console.pack()

        # Add text widget to display logging info
        self.textbox = Text(frame, height=4)
        self.textbox.pack()

        self.textbox.bind("<Return>", self.cmd_send)

    def __loop_receive(self):
        try:
            while True:
                msg = self.connection.recv(MAX_LENGTH).decode("utf-8")
                self.console.insert(self.console.index('end'), msg + "\n")
        except ConnectionResetError:
            self.console.insert(self.console.index('end'), "Server unexpectedly closed\n")

    def exit(self):
        self.connection.close()

        self.destroy()
        self.root.destroy()

    def cmd_send(self, event):
        msg = self.textbox.get("1.0", "end").strip()
        self.textbox.delete("1.0", "end")

        self.console.insert(self.console.index('end'), "Me> " + msg + "\n")

        self.connection.sendall(msg.encode("utf-8"))


def init():
    root = tk.Tk()
    MainWindow(root)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    init()
