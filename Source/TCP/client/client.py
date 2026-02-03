import socket
import struct
import threading
import os
import sys
import time

def clear_console():
    """Xóa toàn bộ nội dung trong console trước khi bắt đầu hiển thị mới."""
    os.system('cls' if os.name == 'nt' else 'clear')

def read_input_file():
    """Đọc danh sách file từ input.txt."""
    try:
        with open("input.txt", "r") as f:
            files = [line.strip() for line in f if line.strip()]
        return files
    except FileNotFoundError:
        print("Không tìm thấy input.txt! Không có file nào được tải.")
        return []

def download_chunk(server_ip, server_port, file_name, offset, chunk_size, progress, index, lines):
    """Tải một chunk từ server và cập nhật tiến trình."""
    try:
        output_path = f"downloaded_files/{file_name}.part{index}"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((server_ip, server_port))
            request = f"{file_name} {offset} {chunk_size}"
            sock.sendall(request.encode())

            # Nhận header
            header = sock.recv(4)
            if len(header) < 4:
                raise ValueError(f"Header nhận từ server không đầy đủ: {header}")

            data_size = struct.unpack('!I', header)[0]
            if data_size == 0:
                raise ValueError(f"Chunk {index + 1} trống hoặc không được nhận đúng cách.")

            # Tải dữ liệu
            received = 0
            with open(output_path, 'wb') as f:
                while received < data_size:
                    chunk = sock.recv(min(1024, data_size - received))  # Nhận theo block 1KB
                    if not chunk:
                        raise ValueError(f"Không nhận đủ dữ liệu cho chunk {index + 1}")
                    f.write(chunk)
                    received += len(chunk)

                    # Cập nhật tiến độ
                    progress[index] = int((received / data_size) * 100)
                    lines[index] = f"Downloading {file_name} part {index + 1} .... {progress[index]}%"

            # Khi hoàn thành
            progress[index] = 100
            lines[index] = f"Downloading {file_name} part {index + 1} .... 100%"
    except Exception as e:
        lines[index] = f"Downloading {file_name} part {index + 1} .... ERROR: {e}"
        progress[index] = -1  # Đánh dấu lỗi cho chunk này

def display_progress(lines, stop_event):
    """Hiển thị tiến trình với 4 dòng cố định và không nuốt dòng."""
    printed_lines = 0
    while not stop_event.is_set():
        if printed_lines == 0:
            print("\n".join(lines))  # In lần đầu tiên
            printed_lines = len(lines)
        else:
            sys.stdout.write("\033[F" * len(lines))  # Quay lại đầu của nhóm 4 dòng
            for line in lines:
                sys.stdout.write(f"{line}\033[K\n")  # Xóa phần dư và ghi lại nội dung
        sys.stdout.flush()
        time.sleep(0.1)

def merge_chunks(file_name, chunk_files):
    """Ghép các chunk thành file hoàn chỉnh."""
    save_path = os.path.join("downloaded_files", file_name)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    with open(save_path, 'wb') as final_file:
        for chunk_file in chunk_files:
            with open(chunk_file, 'rb') as f:
                final_file.write(f.read())
            os.remove(chunk_file)  # Xóa chunk sau khi ghép

    return save_path

def download_file(server_ip, server_port, file_name, file_size):
    """Tải file bằng cách chia thành 4 chunk và tải song song."""
    chunk_size = file_size // 4
    threads = []
    progress = [0] * 4
    lines = [f"Downloading {file_name} part {i + 1} ....   0%" for i in range(4)]
    stop_event = threading.Event()

    # Khởi chạy luồng hiển thị tiến trình
    display_thread = threading.Thread(target=display_progress, args=(lines, stop_event))
    display_thread.start()

    # Tạo các luồng tải chunk
    for i in range(4):
        offset = i * chunk_size
        actual_chunk_size = chunk_size if i < 3 else file_size - offset

        thread = threading.Thread(target=download_chunk,
                                  args=(server_ip, server_port, file_name, offset, actual_chunk_size, progress, i, lines))
        threads.append(thread)
        thread.start()

    # Đợi tất cả các luồng hoàn thành
    for thread in threads:
        thread.join()

    # Dừng hiển thị tiến trình khi tải xong
    stop_event.set()
    display_thread.join()

    # Ghép các chunk lại thành file hoàn chỉnh
    chunk_files = [f"downloaded_files/{file_name}.part{i}" for i in range(4)]
    merge_chunks(file_name, chunk_files)

    # In thông báo hoàn thành file
    print(f"File {file_name} đã được tải xuống thành công.")

def main():
    downloaded_files = set()  # Tập hợp lưu các file đã tải xong

    try:
        # Kết nối tới server để lấy danh sách file
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('127.0.0.1', 9000))
            sock.sendall(b"GET_FILE_LIST")
            data = sock.recv(4096).decode()

            file_list = []
            for line in data.split("\n"):
                if line.strip():
                    file_name, file_size = line.split(',')
                    file_list.append((file_name.strip(), int(file_size.strip())))

        # Hiển thị danh sách file trên server (chỉ in 1 lần)
        print("Danh sách file có sẵn trên server:")
        available_files = {file_name: file_size for file_name, file_size in file_list}
        for file_name, file_size in available_files.items():
            size_in_mb = file_size / (1024 * 1024)  # Chuyển từ byte sang MB
            print(f"- {file_name}: {size_in_mb:.2f} MB")  # Hiển thị 2 chữ số thập phân


    except Exception as e:
        print(f"Lỗi khi kết nối tới server: {e}")
        return

    while True:
        try:
            # Đọc danh sách file từ input.txt
            input_files = read_input_file()
            if not input_files:
                print("Danh sách trong input.txt trống! Không có file nào được tải.")
                time.sleep(5)
                continue

            # Tải các file từ danh sách input.txt
            for file_name in input_files:
                if file_name in available_files and file_name not in downloaded_files:
                    print(f"\nĐang tải {file_name}...")
                    download_file('127.0.0.1', 9000, file_name, available_files[file_name])
                    downloaded_files.add(file_name)

            # Chờ 5 giây trước khi kiểm tra lại danh sách file từ input.txt
            print("\nChờ 5 giây để kiểm tra lại danh sách file từ input.txt...")
            time.sleep(5)

        except FileNotFoundError:
            print("Không tìm thấy input.txt! Vui lòng tạo file này trong cùng thư mục với client.py.")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nĐã dừng chương trình.")
            break
        except Exception as e:
            print(f"Lỗi không xác định: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()

