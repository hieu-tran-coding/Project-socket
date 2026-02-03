from genericpath import exists
import socket
#For file monitoring
import time
import os
import os.path
import struct

import signal
import sys

#Close program using ctrl+C
def handle_ctrl_c(signum, frame,):
    print("\nProgram stopped by Ctrl+C.")
    sys.exit(0)
# Register the signal handler for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, handle_ctrl_c)


class packet():
    #Init a package with payload, seq and ack numbers
    def __init__(self,payload,length,seq,ack,chunk_index):
        self.payload= payload
        self.length = length

        self.seq = seq;
        self.ack = ack;
        self.chunk_index = chunk_index
        self.checksum = 0

    def calculate_checksum(self)->int:
        # Combine header fields and payload into a single byte sequence for checksum
        header_data = struct.pack('!IIII', self.seq, self.ack, self.length,self.chunk_index)
        data = header_data + self.payload
        checksum = sum(data) & 0xFFFF  # Calculate checksum (16-bit)
        return checksum
   
    def serialize(self):
        self.checksum = self.calculate_checksum()
        # Create header: seq, ack, length, checksum, chunk index
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







INPUT_PATH   = "input.txt"
SERVER_IP   = "127.0.0.1"
SERVER_PORT = 12345
BUFFER_SIZE = 1024
SMALLEST_SIZE = 600002
PKT_SIZE = 30000
HEADER_SIZE = 18
def client_program():

   

    #Create socket
    client_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    server_address = (SERVER_IP,SERVER_PORT)





    if(send_hello(client_socket,server_address,"Hello","ACK_Hello")):
        print(f"Client can send and receive ACK from {server_address}")
    else :
        return

    #Print out files list
    print("----Files list from server----")
    while True:
        msg,addr = client_socket.recvfrom(BUFFER_SIZE)
        if msg.decode() == "END":
            break
        print(msg.decode())

    #Request a file from external txt file
    while True:
        for reqFileName in monitoring_input(INPUT_PATH,5):

            if(os.path.exists(f"downloaded_files/{reqFileName}")):
                print(f"File {reqFileName} already exist on client")
                continue
           
            file_size = request_file_from_server(client_socket,server_address,reqFileName)
            if(file_size):

                #Split file and its extension 
                basename, extension = os.path.splitext(reqFileName)
                if(file_size <= SMALLEST_SIZE):
                    chunk_count = 4   
                else:
                    chunk_count = file_size //PKT_SIZE
                if(file_size <PKT_SIZE):
                    chunk_count = 1 
                
            

                receive_file(client_socket,server_address,basename,file_size,chunk_count)

                merge_chunk(basename,extension,chunk_count)
                
                print(f"Receive file {reqFileName} complete")
            else:
                pass

    client_socket.close()



def monitoring_input(filePath, interval):
   try:
        with open(filePath, 'r') as file:
            # Move to the end of the file initially
            file.seek(0, os.SEEK_END)

            while True:
                line = file.readline()
                if line:
                    yield line.strip()  # Return the new line without trailing whitespace
                else:
                    time.sleep(interval)  # Wait before checking again
   except FileNotFoundError:
        print(f"File not found: {filePath}")
   except Exception as e:
        print(f"An error occurred: {e}")
         
def send_hello(client_socket,server_address,CONNECT_message,ACK_message,timeout = 5,max_retries = 5)->bool:
    client_socket.settimeout(timeout)
    for attempt in range(max_retries):    
        try:
            client_socket.sendto(CONNECT_message.encode(),server_address)

            #Waiting ...
            msg,addr = client_socket.recvfrom(BUFFER_SIZE)
            if msg.decode().strip() == ACK_message:
                client_socket.settimeout(None)
                return True

        except socket.timeout:
            print(f"Attempt {attempt + 1}: Request timed out after {timeout} seconds.")
    else:
        print("Socket failed to connect to server")
        return False

def request_file_from_server(client_socket,server_address,file_name,timeout = 5,max_retries = 10)->int:
        client_socket.settimeout(timeout)
        for attempt in range(max_retries):    
            try:
                client_socket.sendto(file_name.encode(),server_address)

                #Waiting ...
                msg,addr = client_socket.recvfrom(BUFFER_SIZE)
                reply = msg.decode().strip()
                if  reply == "NO":
                    client_socket.settimeout(None)
                    return 0
                if reply != None:
                    client_socket.settimeout(None)
                    return int(reply)

            except socket.timeout:
                print(f"Attempt {attempt + 1}: Request timed out after {timeout} seconds.")
        else:
            print("Socket failed to connect to server")

def receive_file(client_socket, server_address, file_name, file_size, chunk_count):
    if not os.path.exists("downloaded_files"):
        os.makedirs("downloaded_files")
        
    chunk_size = file_size // chunk_count
    
    print(f'\nReceiving {file_name} ({file_size/1024/1024:.2f} MB)')
    received_chunks = 0
    
    for i in range(chunk_count):
        # Skip if chunk already exists
        if os.path.exists(f"downloaded_files/{file_name}.part{i}"):
            received_chunks += 1
            progress = (received_chunks / chunk_count) * 100
            print(f"\rProgress: {progress:.1f}% ({received_chunks}/{chunk_count} chunks)", end='')
            continue
            
        download_size = chunk_size if i < chunk_count - 1 else file_size - (i * chunk_size)
        expected_packet_size = download_size + HEADER_SIZE
        
        while True:
            try:
                # Receive data packet directly
                data, addr = client_socket.recvfrom(expected_packet_size + 100)  # Add small buffer for safety
                
                # Check packet length
                if len(data) < HEADER_SIZE:
                    #print(f"\nReceived incomplete packet (length: {len(data)}), requesting retransmission...", end='')
                    continue
                    
                # Try to deserialize the packet
                try:
                    pkt = packet.deserialize(data)
                    
                    # Verify chunk index and checksum
                    if pkt.chunk_index != i:
                        #print(f"\nReceived wrong chunk (expected {i}, got {pkt.chunk_index}), requesting retransmission...", end='')
                        continue
                        
                    if pkt.checksum != pkt.calculate_checksum():
                        #print(f"\nChecksum verification failed for chunk {i}, requesting retransmission...", end='')
                        continue
                    
                    # Write chunk to file if all validations pass
                    output_path = f"downloaded_files/{file_name}.part{i}"
                    with open(output_path, 'wb') as f:
                        f.write(pkt.payload)
                        
                    # Send acknowledgment
                    ack_pkt = packet(b"", pkt.length, pkt.seq, pkt.seq + pkt.length, pkt.chunk_index)
                    client_socket.sendto(ack_pkt.serialize(), server_address)
                    
                    # Update progress
                    received_chunks += 1
                    progress = (received_chunks / chunk_count) * 100
                    print(f"\rProgress: {progress:.1f}% ({received_chunks}/{chunk_count} chunks)", end='')
                    break
                    
                except ValueError as e:
                    #print(f"\nPacket deserialization failed: {e}, requesting retransmission...", end='')
                    continue
                    
            except socket.timeout:
                print(f"\rTimeout receiving chunk {i}, retrying...", end='')
                continue
            except Exception as e:
                print(f"\rUnexpected error receiving chunk {i}: {e}, retrying...", end='')
                continue
    
    print("\nTransfer complete!")

def merge_chunk(file_name,extension,chunk_count)->bool:

    for i in range(chunk_count):
            
        if(os.path.exists(f"downloaded_files/{file_name}.part" + str(i))):
            if(i == chunk_count - 1):
                print(f"Merging chunk for {file_name} ...")
             
        else :
            print(f"Missing chunk {i}")
            return False

    save_path = os.path.join("downloaded_files", file_name + extension)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    with open(save_path, 'wb') as final_file:
        for  i in range(chunk_count):
            chunk_file = f"downloaded_files/{file_name}.part" + str(i)

            with open(chunk_file, 'rb') as f:
                final_file.write(f.read())

            os.remove(chunk_file)  # Delete chunk after writing

    return True




if __name__ == "__main__":
    client_program()