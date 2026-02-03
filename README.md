# Socket Programming Project: Multi-protocol File Transfer

This project implements a file transfer system using Python's `socket` library. It features two separate implementations: one based on **TCP** for reliable, multi-threaded downloads, and another based on **UDP** utilizing a custom Reliable Data Transfer (RDT) mechanism.

## 🚀 Features

### TCP Implementation
* **Multi-threading:** Downloads files by splitting them into 4 parallel chunks for increased speed.
* **Progress Tracking:** Real-time terminal display showing the percentage completion of each individual chunk.
* **Automatic Merging:** Automatically combines received chunks into a final complete file.

### UDP Implementation
* **Reliable Data Transfer (RDT):** Custom packet structure including `Sequence Number`, `ACK`, `Checksum`, and `Chunk Index` to ensure data integrity over UDP.
* **Error Handling:** Implements timeouts and a maximum retry mechanism for lost packets.
* **Integrity Verification:** Uses bitwise checksums to detect and handle corrupted data.

## 🛠️ Installation & Setup

### Prerequisites
* Python 3.x
* Basic understanding of terminal/command prompt.

### Configuration
Before running, ensure the server and client are configured with the correct IP addresses. By default, they are set to `127.0.0.1` (loopback).

1.  **Server side:** Place the files you want to share in a folder named `files/`.
2.  **Client side:** Create a file named `input.txt` in the client directory. This file is used to request specific downloads by typing the filename into it.

## 📖 How to Use

### Running TCP
1.  Navigate to `Source/TCP/server/` and run: `python server.py`.
2.  Navigate to `Source/TCP/client/` and run: `python client.py`.
3.  Add the desired filename (e.g., `Video.mp4`) to `input.txt` at the client side to begin the download.

### Running UDP
1.  Navigate to `Source/UDP/server/server/` and run: `python server.py`.
2.  Navigate to `Source/UDP/client/client/` and run: `python client.py`.
3.  The client will display the available files from the server. Add the filename to `input.txt` to start the reliable UDP transfer.

## 👥 Contributors
* **Trần Trung Hiếu** - (UDP Implementation & Report)
* **Vũ Duy Thụ** - (TCP Implementation)

---
*Project developed for the Faculty of Information Technology, University of Science (VNU-HCM) - 2024.*
