import tkinter as tk
from tkinter import Text, Button, Entry, Scrollbar
from threading import Thread
import socket


MAX_MSG_LENGTH = 2056


class MainWindow(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent

        self.__build_gui()

        self.connection = None
        self.receive_thread = None

        self.greeted = False

        self.log("Top windows shows messages, bottom window sends messages")
        self.log("Press enter to send your message")

    def __build_gui(self):
        self.root.title("Text Chat")
        self.root.option_add('*tearOff', 'FALSE')

        connection_frame = tk.Frame(master=self.root)
        connection_frame.pack(side=tk.LEFT, padx=10, pady=10)

        base_frame = tk.Frame(master=self.root)
        base_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        text_frame = tk.Frame(master=base_frame)
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(connection_frame, text='IP and port of server').pack()
        self.ip = Entry(connection_frame, width=20)
        self.ip.insert(tk.END, "localhost:8888")
        self.ip.pack()

        Button(connection_frame, text='Connect', command=self.cmd_connect).pack(pady=5)
        Button(connection_frame, text='Disconnect', command=self.cmd_disconnect).pack()

        self.console = Text(text_frame, height=10)
        self.console.pack(fill=tk.BOTH, expand=True)

        scrollbar = Scrollbar(base_frame, command=self.console.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.console["yscrollcommand"] = scrollbar.set

        self.textbox = Text(text_frame, height=3)
        self.textbox.pack(fill=tk.BOTH, expand=True)

        self.textbox.bind("<Return>", self.cmd_send)

    def __loop_receive(self):
        try:
            while True:
                msg = self.connection.recv(MAX_MSG_LENGTH).decode("utf-8")

                if not self.greeted:
                    self.greeted = True
                    if msg == "welcome":
                        self.log("Connected to server")
                        continue
                    elif msg == "full":
                        self.log("Server is full")
                        self.cmd_disconnect()
                        return

                self.log(msg)
        except ConnectionResetError:
            self.log("Server unexpectedly closed")
        except ConnectionAbortedError:
            self.log("Connection closed")

    def exit(self):
        self.connection.close()

        self.destroy()
        self.root.destroy()

    def cmd_send(self, event):
        msg = self.textbox.get("1.0", "end").strip()
        self.textbox.delete("1.0", "end")

        if self.connection:
            self.log("Me> " + msg)
            self.connection.sendall(msg.encode("utf-8"))
        else:
            self.log("No active connections")

    def cmd_connect(self):
        if self.receive_thread is not None or self.connection is not None:
            self.log("A connection is already active")
            return

        try:
            ip = self.ip.get().split(":")[0]
            port = int(self.ip.get().split(":")[1])
        except (ValueError, IndexError):
            self.log("Invalid IP")
            return

        self.greeted = False

        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.connect((ip, port))
        self.receive_thread = Thread(target=self.__loop_receive, daemon=True)
        self.receive_thread.start()

    def cmd_disconnect(self):
        if not self.receive_thread or not self.receive_thread.is_alive():
            self.log("No active connections")
            return

        self.connection.close()

        self.connection = None
        self.receive_thread = None

    def log(self, msg):
        self.console.insert(self.console.index('end'), msg + "\n")
        self.console.see(tk.END)


def init():
    root = tk.Tk()
    MainWindow(root)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    init()
