import socket
import os
import threading
import struct

FILE_LIST = "files.txt"

def load_file_list():
    """
    Đọc danh sách file từ files.txt.
    """
    files = {}
    with open(FILE_LIST, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                try:
                    # Xử lý giá trị kích thước thập phân
                    size_in_mb = float(parts[1].upper().replace('MB', ''))
                    files[parts[0]] = int(size_in_mb * 1024 * 1024)
                except ValueError:
                    print(f"Lỗi: Không thể xử lý kích thước file '{line.strip()}'")
    return files


def send_chunk(client_socket, file_name, offset, chunk_size):
    """
    Gửi một chunk của file từ offset với kích thước chunk_size.
    """
    try:
        file_path = os.path.join("files", file_name)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File không tồn tại: {file_path}")

        with open(file_path, 'rb') as f:
            f.seek(offset)
            data = f.read(chunk_size)
            header = struct.pack('!I', len(data))
            client_socket.sendall(header + data)
    except FileNotFoundError as e:
        print(f"Lỗi khi gửi chunk: {e}")
        client_socket.sendall(struct.pack('!I', 0))
    except Exception as e:
        print(f"Lỗi khi gửi chunk: {e}")

def handle_client(client_socket, file_list):
    """
    Xử lý yêu cầu từ client.
    """
    try:
        while True:
            request = client_socket.recv(1024).decode()
            if not request:
                break

            if request == "GET_FILE_LIST":
                response = "\n".join(f"{name},{size}" for name, size in file_list.items())
                client_socket.sendall(response.encode())
            else:
                parts = request.split()
                if len(parts) == 3:
                    file_name, offset, chunk_size = parts[0], int(parts[1]), int(parts[2])
                    if file_name in file_list:
                        send_chunk(client_socket, file_name, offset, chunk_size)
                    else:
                        client_socket.sendall(b"ERROR: File not found.")
    except Exception as e:
        print(f"Lỗi xử lý client: {e}")
    finally:
        client_socket.close()

def start_server(host='127.0.0.1', port=9000):
    """
    Khởi động server và xử lý kết nối từ client.
    """
    file_list = load_file_list()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print("Server đang hoạt động...")
    print("Đang chờ kết nối từ client...")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Kết nối từ {addr}")
        threading.Thread(target=handle_client, args=(client_socket, file_list)).start()

if __name__ == "__main__":
    start_server()
