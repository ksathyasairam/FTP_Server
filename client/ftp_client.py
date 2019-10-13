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

class ftp_client():
    def __init__(self):
        self.tcp_client_socket = None
        self.file_upload_socket = None

        # infinite loop to procees commands

        while (1):
            input_string = raw_input("\nEnter Command -> ")
            command = input_string.lower().strip(" ").split(" ")
            if command[0] == "quit":
                if not self.tcp_client_socket:
                    exit()
                self.quit(command)
            elif command[0] == "dir":
                if not self.tcp_client_socket:
                    print("\nServer not connected. Connect using ftp_client command. < ftp_client IP PORT >")
                    continue
                self.dir(command)
            elif command[0] == "get":
                if not self.tcp_client_socket:
                    print("\nServer not connected. Connect using ftp_client command. < ftp_client IP PORT >")
                    continue
                self.get(command)
            elif command[0] == "upload":
                if not self.tcp_client_socket:
                    print("\nServer not connected. Connect using ftp_client command. < ftp_client IP PORT >")
                    continue
                self.upload(command)
            elif command[0] == "ftp_client":
                self.ftp_client(command)
            elif command[0] == "authenticate":
                self.authenticate(command)
            else:
                print("\nUnknown command: '" + command[0] + "'")
    def ftp_client(self,command):
        try:
            # if connection already exists close the connection and start new connection
            if self.tcp_client_socket:
                if "-f" in command :
                    command.pop()
                    self.send_message_to_server("quit")
                    print("\nServer said:",str(self.tcp_client_socket.recv(BUFFER_SIZE)).rstrip("\r\n"))
                    self.tcp_client_socket.close()
                else:
                    print("client already connected to server. To reconnect use -f for force")
                    return

            # open socket conneciton for file upload
            self.file_upload_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.file_upload_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.file_upload_socket.bind((IP,UPLOAD_PORT))
            self.file_upload_socket.listen(1)
            self.tcp_client_socket = socket.socket()

            IP_TO_CONNECT = IP
            PORT_TO_CONNECT = PORT
            if len(command) == 3:
                IP_TO_CONNECT = command[1]
                PORT_TO_CONNECT = int(command[2])
            elif len(command) == 2:
                IP_TO_CONNECT = command[1]
                print("\nMissing Params : PORT. Missing param was set to default value.\n\nPORT : " + str(PORT_TO_CONNECT))
            elif len(command) == 1:
                print("\nMissing Params : IP, PORT. Missing param were set to default value.\n\nIP: "+ str(IP_TO_CONNECT)+" PORT:"+str(PORT_TO_CONNECT))

            print("\nEstablishing connection to server: " + str(IP_TO_CONNECT) + ":" + str(PORT_TO_CONNECT))

            try:
                self.tcp_client_socket.connect((IP_TO_CONNECT,PORT_TO_CONNECT))
            except Exception as err:
                print(err)
                print("\nUnable to establish successfull connection with the server. Try Again!")
                if self.tcp_client_socket :
                    self.tcp_client_socket = None
                if self.file_upload_socket:
                    self.file_upload_socket.close()
                    self.file_upload_socket = None
                return

            print("\nConnection established ... ^__^")
            return

        except Exception as err:
            print(err)
            print("\nError in ftp_client connection command. Try again!  ")
            if self.tcp_client_socket :
                self.tcp_client_socket = None
            if self.file_upload_socket:
                self.file_upload_socket.close()
                self.file_upload_socket = None
            return

    # function to authenticate
    def authenticate (self,command):
        print("\nExecuting authenticate Command")
        self.send_message_to_server("authenticate")
        while(1):
            response = str(self.tcp_client_socket.recv(BUFFER_SIZE)).rstrip("\r\n")
            if "Enter Credntials" in response:
                username = raw_input("\nEnter Username :")
                password = raw_input("\nEnter Password :")
                self.send_message_to_server(username+" "+password)
                response = str(self.tcp_client_socket.recv(BUFFER_SIZE)).rstrip("\r\n")
                if  "unauthenticated" not in response.lower():
                    print("\nAuthentication successfull.")
                    return
                else:
                    print("\nAuthentication unsuccessfull.")
                    return
            else:
                if "authenticated" in response.lower():
                    print("\nAlready authenticated.")
                    return


    # function to quit
    def quit(self,command):
        print("\nExecuting Quit Command")
        try:
            self.send_message_to_server("quit")
            print("\nServer said : "+str(self.tcp_client_socket.recv(BUFFER_SIZE)).rstrip("\r\n"))
            self.tcp_client_socket.close()
        except:
            exit()
        exit()

    # function to get directory from server
    def dir(self,command):
        print("\nExecuting Dir Command")
        self.send_message_to_server(" ".join(command))

        response = str(self.tcp_client_socket.recv(BUFFER_SIZE)).rstrip("\r\n")
        if "UnAuthenticated" in response:
            print("\nClient not authenticated. Please run authenticate command")
            return
        else:
            print("\nFile\n-------------------\n")
            while(1):
                data = str(self.tcp_client_socket.recv(BUFFER_SIZE)).rstrip("\r\n")
                lines = data.split("\n")
                for line in lines:
                    if line.lower()== "eom":
                        return
                    else:
                        print(line+ "\n")

    # function to download directory from server
    def get(self,command):
        print("\nExecuting Get Command")
        self.send_message_to_server(" ".join(command))
        response = str(self.tcp_client_socket.recv(BUFFER_SIZE)).rstrip("\r\n")
        if "UnAuthenticated" in response:
            print("\nClient not authenticated. Please run authenticate command")
            return
        else:
            received_file = ROOT_DIR +(command[1]).lower().strip() if len(command) == 2 else None
            response = str(self.tcp_client_socket.recv(BUFFER_SIZE)).rstrip("\r\n")
            print(response)
            # checking for start of file marker
            if "sof" in response.lower():
                # removing the marker data
                response = response[(response.find("sof")+2):]
                print(response)
                with open(received_file, 'wb') as file:
                    print ('file opened')
                    data = str(self.tcp_client_socket.recv(BUFFER_SIZE)).rstrip("\r\n")
                    while(1):
                        lines = data.split("\r\n")
                        for line in lines:
                            # checking for end of file marker
                            if line.lower() == "eof":
                                print("\nclosing file after writing")
                                file.close()
                                return
                            else:
                                print('line=%s', (line))
                                file.write(line.rstrip("\n")+"\n")
                        data = str(self.tcp_client_socket.recv(BUFFER_SIZE)).rstrip("\r\n")
                        print("\ndata is",data)


    # function to upload directory from server
    def upload(self,command):
        print("\nExecuting Upload Command")
        # sending port for upload
        command.append(str(UPLOAD_PORT))
        self.send_message_to_server(" ".join(command))
        # removing extra params port for upload
        command.pop()

        response = str(self.tcp_client_socket.recv(BUFFER_SIZE)).rstrip("\r\n")
        if "UnAuthenticated" in response:
            print("\nClient not authenticated. Please run authenticate command")
            return
        else:
            #  waiting for the server to accept the socket connection in an infinite loop
            while(1):
                connection , address = self.file_upload_socket.accept()
                if connection and address:
                    file_to_be_uploaded = ROOT_DIR +(command[1]).lower().strip() if len(command) >= 2 else None
                    if not file_to_be_uploaded:
                        print("\nNo file mentioned for upload in the params")
                        connection.close()
                        return

                    print("\nRequested File to be upload_file:" + str(file_to_be_uploaded))
                    path_to_be_uploaded = os.path.abspath(file_to_be_uploaded)
                    if not os.path.exists(path_to_be_uploaded):
                        print("\nNo such file exists at the path")
                        connection.close()
                        return
                    print("\nStarting File Upload")

                    # read file and send data
                    file = open(path_to_be_uploaded,'rb')
                    while True:
                        line = file.readline()
                        print(line)
                        while (line):
                            self.send_message_to_server_for_upload(line,connection)
                            print('Sent ',repr(line))
                            line = file.readline()
                            if not line:
                                # if file finished close file and socket
                                file.close()
                                connection.close()
                                print("\nFinished File Upload")
                                return
    # function to send message to server socket
    def send_message_to_server(self,message):
        self.tcp_client_socket.sendall(bytearray(message + "\r\n", "utf-8"))
    # function to send message to server socket for file upload
    def send_message_to_server_for_upload(self,message,connection):
        connection.sendall(bytearray(message + "\r\n", "utf-8"))

if __name__ == '__main__':
  # start the client
  server = ftp_client()
