import queue
import socket
import xml.etree.ElementTree as ET
import threading

port = 2605
host = "127.0.0.1"

# IDLE message
idle_message: str = """
\x02
<TerminalStatusEMV>
<MerchantTransactionID>2</MerchantTransactionID>
<ZRNumber>2055</ZRNumber>
<DeviceNumber>601</DeviceNumber>
<DeviceType>6</DeviceType>
<TerminalID>Term01</TerminalID>
<Date>250312</Date>
<Time>140058</Time>
<TimeOffset>UTC+01</TimeOffset>
<VersionProtocol>1.25</VersionProtocol>
<VersionEMVFirmware>123_10Q</VersionEMVFirmware>
<ResponseStatus>STATUS</ResponseStatus>
<ResponseCode>100</ResponseCode>
<ResponseTextMessage>Idle</ResponseTextMessage>
</TerminalStatusEMV>
\x03
"""


class ConnectionHandler:
    def __init__(self):
        self.idle_message_event = threading.Event()
        self.idle_message_thread = None

    def send_idle_message(self, conn: socket.socket, timeout: int):
        self.idle_message_event.clear()
        while not self.idle_message_event.wait(timeout - 1):
            if self.idle_message_event.is_set():
                break
            conn.sendall(idle_message.encode())
            print("INFO: Sent idle message")

    def kill_idle_message_thread(self):
        if self.idle_message_thread and self.idle_message_thread.is_alive():
            self.idle_message_event.set()  # Signal the thread to stop
            self.idle_message_thread.join()  # Wait for it to exit

    def handle_connection(self, conn: socket.socket):
        while True:
            data = conn.recv(4096)
            if not data:
                print("INFO: Client disconnected")
                self.kill_idle_message_thread()
                break

            print("INFO: Received data")

            xml_data = data.decode()
            xml = clean_xml(xml_data)
            root = ET.fromstring(xml)
            timeout = int(root.find("TimeoutResponse").text)

            self.kill_idle_message_thread()

            # Start a new idle message thread
            self.idle_message_event.clear()
            self.idle_message_thread = threading.Thread(
                target=self.send_idle_message, args=(conn, timeout))
            self.idle_message_thread.start()


def clean_xml(xml: str) -> str:
    return xml.strip("\x02\x03")


def listen_for_connections(socket: socket.socket, connections: queue.Queue):
    while True:
        conn, _ = socket.accept()
        connections.put(conn)


def main() -> None:
    print(f"listening on port: {port}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", port))

    server.listen(1)

    connections = queue.Queue()
    listener_thread = threading.Thread(
        target=listen_for_connections, args=(server, connections), daemon=True)
    listener_thread.start()

    connection_handler = ConnectionHandler()

    while True:
        conn = connections.get()
        connection_handler.handle_connection(conn)


if __name__ == "__main__":
    main()
