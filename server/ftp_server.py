import socket
from threading import Thread
from SocketServer import ThreadingMixIn
import sys
import os
import pdb

IP = 'localhost'
PORT = 9000
BUFFER_SIZE = 2048
ROOT_DIR = "./root/"
UPLOAD_PORT = 9001


# command thread to handle clients individually
class command_processor_thread(Thread):
    def __init__(self, socket):
        Thread.__init__(self)
        self.server_socket = socket
        self.finished_running = False
        self.isClientAuthenticated= False

    # loop infinitely and process commands till the client quits and kills the thread.
    def run(self):
        while(1):
            command = str(self.server_socket.recv(BUFFER_SIZE)).rstrip("\r\n")
            print(command)
            if command:
                split= command.lower().split(" ")
                print("Command received -------->",split)
                try:
                    getattr(self,split[0])(split)
                except:
                    self.send_message_to_client(" Unknow Command ")
            if self.finished_running:
                self.server_socket.close()
                return
    # function to quit
    def quit(self,command):
        print("Quit Command")
        self.send_message_to_client("221 closing socket")
        self.finished_running = True

    # function to give directory of files
    def dir(self,command):
        print("Dir Command",command)
        # authentication check
        if self.isClientAuthenticated:
            # send flag for authentication.
            self.server_socket.sendall(bytearray("Authenticated", "utf-8"))

            # check for the requested directory
            requested_dir = ROOT_DIR+(command[1]).lower().strip() if len(command) == 2 else ROOT_DIR
            print(requested_dir)
            try:
                files_in_dir = os.listdir(os.path.abspath(requested_dir))
            except:
                self.server_socket.sendall(bytearray("EOM", "utf-8"))
                return

            files_in_dir.sort()
            file_string = ""
            for file in files_in_dir:
                file_string = file_string + file + "\n"
            print(file_string)
            self.server_socket.sendall(bytearray(file_string, "utf-8"))
            # sending end of message marker
            self.server_socket.sendall(bytearray("EOM", "utf-8"))
        else:
            self.server_socket.sendall(bytearray("UnAuthenticated", "utf-8"))

    # function to enable file download from the directory of files
    def get(self,command):
        print("Get Command")
        # authentication check
        if self.isClientAuthenticated:
            self.server_socket.sendall(bytearray("Authenticated", "utf-8"))
            requested_file = ROOT_DIR +(command[1]).lower().strip() if len(command) == 2 else None
            if not requested_file:
                self.server_socket.send(bytearray("Invalid Params: Please mention a file to get" + "\r\n", "utf-8"))
                return

            # check for the requested file
            print("Requested File :",requested_file)
            requested_file_path = os.path.abspath(requested_file)
            if not os.path.exists(requested_file_path):
                self.server_socket.send(bytearray("No such file exists at the server. :"+ str(requested_file_path) + "\r\n", "utf-8"))
                return

            # read file and send data
            file = open(requested_file_path,'rb')
            print("sending SOF")
            self.server_socket.send(bytearray("SOF" + "\r\n", "utf-8"))
            while True:
                line = file.readline()
                print(line)
                while (line):
                    self.server_socket.send(bytearray(line + "\r\n", "utf-8"))
                    print('Sent ',repr(line))
                    line = file.readline()
                if not line:
                    file.close()
                    print("sending EOF")
                    self.server_socket.send(bytearray("EOF" + "\r\n", "utf-8"))
                    break
            print("Finished Sending File")
        else:
            self.server_socket.sendall(bytearray("UnAuthenticated", "utf-8"))

    # function to enable file upload from the directory of file
    def upload(self,command):
        # authentication check
        if self.isClientAuthenticated:
            self.server_socket.sendall(bytearray("Authenticated", "utf-8"))
            print("Upload Command")
            try:
                print("connecting to the client socket for upload")
                server_socket = socket.socket()
                PORT_FOR_UPLOAD = int(command[2]) if len(command) ==3 else UPLOAD_PORT
                server_socket.connect((IP,PORT_FOR_UPLOAD))
            except:
                print("Unable to connect")
            print("Connection established with client for upload")

            received_file = ROOT_DIR +(command[1]).lower().strip() if len(command) >= 2 else None
            data = str(server_socket.recv(BUFFER_SIZE)).rstrip("\r\n")
            if data:
                # open file and write data
                with open(received_file, 'wb') as file:
                    print ('file opened for upload')
                    while(data):
                        lines = data.split("\r\n")
                        for line in lines:
                                print('line=%s', (line))
                                file.write(line.rstrip("\n")+"\n")
                        data = str(server_socket.recv(BUFFER_SIZE)).rstrip("\r\n")
                        print("data is",data)
                        if not data:
                            print("closing file after writing")
                            file.close()
                            server_socket.close()
                            break
        else:
            self.server_socket.sendall(bytearray("UnAuthenticated", "utf-8"))

    # funciton to authenticate client
    def authenticate(self,command):
        print("Authenticate Command")
        # authentication check
        if not self.isClientAuthenticated:
            while(1):
                self.send_message_to_client("Enter Credntials")
                credentials = str(self.server_socket.recv(BUFFER_SIZE)).rstrip("\r\n").split(" ")
                if len(credentials) !=2:
                    self.isClientAuthenticated = False
                    self.send_message_to_client("Unauthenticated")
                    print("Authentication unsuccessfull.")
                    return
                elif credentials[0] == "username" and credentials[1]== "password":
                    self.isClientAuthenticated = True
                    self.send_message_to_client("Authenticated")
                    print("Authentication successfull.")
                    return
                else:
                    self.isClientAuthenticated = False
                    self.send_message_to_client("Unauthenticated")
                    print("Authentication unsuccessfull.")
                    return
        else:
            self.send_message_to_client("Authenticated")

    # funciton to send message to client
    def send_message_to_client(self,message):
        self.server_socket.sendall(bytearray(message + "\r\n", "utf-8"))

# class for ftp_server
class ftp_server():
    def __init__(self):
        # initiate socket to listen.
        self.tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_server_socket.bind((IP,PORT))
        self.tcp_server_socket.listen(1)

        print ("Listening for Incoming connections ...")

        # Loop infinitely to accept connection and spawn command_processor_thread for processing data
        while (1):
            connection , address = self.tcp_server_socket.accept()
            print("Accepted Connection from :",address)
            # spawning new thread for incoming client
            thread = command_processor_thread(connection)
            thread.start()

if __name__ == '__main__':
  # start the server
  server = ftp_server()
