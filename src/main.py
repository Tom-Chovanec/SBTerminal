import queue
import socket
import xml.etree.ElementTree as ET
import threading
import time

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

def clean_xml(xml: str) -> str:
    return xml.strip("\x02\x03")


def listen_for_connections(socket: socket, connections: queue.Queue):
    while True:
        conn, _ = socket.accept()
        connections.put(conn)


def main() -> None:
    print(f"listening on port: {port}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", port))

    server.listen(1)

    connections = queue.Queue()
    listener_thread = threading.Thread(target=listen_for_connections, args=(server, connections), daemon=True)
    listener_thread.start()

    while True:
        conn =  connections.get()

        with conn:
            print(f"recieved data")
            data = conn.recv(4096)
            if data:
                xml_data = data.decode()
                xml = clean_xml(xml_data)
                root = ET.fromstring(xml)
                timeout = int(root.find("TimeoutResponse").text)
                time.sleep(timeout -  1)
                print(f"sending idle message")
                conn.sendall(idle_message.encode())


if __name__ == "__main__":
   main()
