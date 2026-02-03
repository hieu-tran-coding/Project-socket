from http import client
import os.path
import socket

import os
#For packet class
import struct

class packet():
    #Init a package with payload, seq and ack numbers
    def __init__(self,payload,length,seq,ack,chunk_index):
        self.payload= payload
        self.length = length
        self.checksum = 0

        self.seq = seq;
        self.ack = ack;
        self.chunk_index = chunk_index

        

    def calculate_checksum(self)->int:
        # Combine header fields and payload into a single byte sequence for checksum
        header_data = struct.pack('!IIII', self.seq, self.ack, self.length,self.chunk_index)
        data = header_data + self.payload
        checksum = sum(data) & 0xFFFF  # Calculate checksum (16-bit)
        return checksum
   

    def serialize(self):
        self.checksum = self.calculate_checksum()        
        # Create header: seq, ack, length, checksum,chunk index
        header = struct.pack('!IIIHI', self.seq, self.ack, self.length, self.checksum,self.chunk_index)
        return header + self.payload  # Combine header and payload

    @staticmethod
    def deserialize(data):
        """Convert binary data back into a Packet object."""
        header = data[:18]  # First bytes are the header
        payload = data[18:]  # The rest is the payload
        seq, ack, length, checksum,chunk_index = struct.unpack('!IIIHI', header)
        pkt = packet(payload,length, seq, ack,chunk_index)
        pkt.length = length
        pkt.checksum = checksum
        pkt.chunk_index = chunk_index
        return pkt





FILE_PATH   = "filesList.txt"
FOLDER_PATH = "files"
SERVER_IP   = "127.0.0.1"
SERVER_PORT = 12345
BUFFER_SIZE = 1024
SMALLEST_SIZE = 60000
PKT_SIZE = 30000
def server_program():
    
    #Create socket
    server_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    server_address = (SERVER_IP, SERVER_PORT)
    server_socket.bind(server_address)
    print(f"Server listening on {server_address}")

   
    #Receive Hello msg and its address from the client
    client_address = receive_hello_and_ack(server_socket,"Hello","ACK_Hello")


    if(client_address!=None):
        print(f"Now receiving message from {client_address}")


    #Send filesList to client
    with open(FILE_PATH, "r") as file:
           for line in file:
               server_socket.sendto(line.strip().encode(),client_address)
    
    server_socket.sendto("END".strip().encode(),client_address) #Indicate finish sending

    #Make file lists to dictionary for easier control
    files = dictionary_conversion()

    #Receive request from client
    while True:
        server_socket.settimeout(None)

        name,addr = server_socket.recvfrom(BUFFER_SIZE)
        reqfile =name.decode().strip()
        send_file(server_socket,client_address,reqfile,files)

    server_socket.close()




def dictionary_conversion():
    file_dict = {}
    with open(FILE_PATH, 'r') as file:
        for line in file:
            # Split the line into filename and size
            parts = line.split(maxsplit=1)
        
            # Extract the filename and size
            filename = parts[0]
            size_str = parts[1].strip()
        
            # Convert the size to MB
            try:
                size_in_mb =  os.path.getsize(os.path.join(FOLDER_PATH,filename))
            except FileNotFoundError :
                print(f"No file exist with name {filename} on server size")

            # Add the entry to the dictionary
            file_dict[filename] = size_in_mb
    return file_dict

def receive_hello_and_ack(server_socket,CONNECT_message,ACK_message,timeout = 5,max_retries = 3)->tuple:
     while True:
        msg,clientAddr = server_socket.recvfrom(BUFFER_SIZE)
        if msg.decode() == CONNECT_message:
            server_socket.sendto(ACK_message.encode(),clientAddr)
            return clientAddr
        
def send_file(server_socket, client_address, reqFile, fileList, timeout=10, max_retries=10):
    if reqFile in fileList:
        file_size = os.path.getsize(os.path.join(FOLDER_PATH,reqFile))
        print(f'\nSending {reqFile} ({file_size/1024/1024:.2f} MB)')
        server_socket.sendto(str(file_size).encode(), client_address)

        # Calculate chunk count
        if file_size <= SMALLEST_SIZE:
            chunk_count = 4
        else:
            chunk_count = file_size // PKT_SIZE
        if(file_size <PKT_SIZE):
            chunk_count = 1 
        chunk_size = file_size // chunk_count
        
        sent_chunks = 0
        last_progress = -1  # Track last printed progress
        
        def update_progress(chunks_done):
            nonlocal last_progress
            progress = (chunks_done / chunk_count) * 100
            # Only update if progress has changed
            if progress != last_progress:
                print(f"\rProgress: {progress:.1f}% ({chunks_done}/{chunk_count} chunks)", end='', flush=True)
                last_progress = progress
        
        for i in range(chunk_count):
            offset = i * chunk_size
            actual_chunk_size = chunk_size if i < chunk_count - 1 else file_size - offset
            if send_chunk(server_socket, client_address, reqFile, offset, actual_chunk_size, i):
                sent_chunks += 1
                update_progress(sent_chunks)
                
        print("\nTransfer complete!")
    else:
        server_socket.sendto("NO".encode(), client_address)
        
def send_chunk(server_socket, client_address, reqFile, offset, chunk_size, chunk_index, timeout=0.1, max_retries=3):
    with open( os.path.join(FOLDER_PATH,reqFile), 'rb') as f:
        f.seek(offset)
        data = f.read(chunk_size)
      
        # Create packet
        pkt = packet(data, chunk_size, offset, offset+chunk_size, chunk_index)
        
        server_socket.settimeout(timeout)
        for attempt in range(max_retries):    
            try:
                # Send packet directly
                server_socket.sendto(pkt.serialize(), client_address)
                
                # Wait for ACK
                ack_data, addr = server_socket.recvfrom(BUFFER_SIZE)
                ack_packet = packet.deserialize(ack_data)
                
                if ack_packet.ack == pkt.ack and ack_packet.seq == pkt.seq:
                    return True
                    
            except socket.timeout:
                print(f"\nAttempt {attempt + 1}: Sending chunk {chunk_index} timed out after {timeout} seconds.")
                continue
                
        print(f"Failed to send chunk {chunk_index} after {max_retries} attempts")
        return False
            




if __name__ == "__main__":
    server_program()
  