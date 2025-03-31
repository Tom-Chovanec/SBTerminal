import socket
import xml.etree.ElementTree as ET
import threading

from xml_parser import XMLParser
from terminal_config import load_config
from message_generator import CardIssuerCode, MessageGenerator, DefaultTags, TerminalStatusResponseCode, TransactionResponseCode, CardType


config = load_config()
default_tags = DefaultTags(
    merchant_transaction_id=2,
    zr_number=2055,
    device_number=601,
    device_type=6,
    terminal_id='Term01'
)


def sendXML(conn, xml: str):
    padded_xml: str = f"\x02\n{xml}\x03"
    conn.sendall(padded_xml.encode())

class ConnectionHandler:
    def __init__(self):
        self.idle_message_event = threading.Event()
        self.idle_message_thread = None

    def send_idle_message(self, conn: socket.socket, timeout: int):
        self.idle_message_event.clear()
        while not self.idle_message_event.wait(timeout - 2):
            if self.idle_message_event.is_set():
                break

            idle_message_dict = MessageGenerator.get_terminal_status_emv_message(
                default_tags=default_tags,
                status_code=TerminalStatusResponseCode.IDLE
            )

            idle_message = XMLParser.dict_to_xml(idle_message_dict)

            sendXML(conn, idle_message)

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

            xml_cleaned = clean_xml(data.decode())
            parsed_xml = XMLParser.parse(xml_cleaned)

            if config.send_rsp_before_timeout:
                # this should probably be reworked
                timeout_value = XMLParser.get_value(parsed_xml, "TimeoutResponse", 0)
                timeout = int(timeout_value) if timeout_value is not None else 0

                self.kill_idle_message_thread()

                # Start a new idle message thread
                if timeout != 0:
                    print(f'INFO: Setting timeout interval to "{timeout}"')
                    self.idle_message_event.clear()
                    self.idle_message_thread = threading.Thread(
                        target=self.send_idle_message, args=(conn, timeout))
                    self.idle_message_thread.start()
                else:
                    print('WARN: Timeout is "0"')


def clean_xml(xml: str) -> str:
    return xml.strip("\x02\x03")


def main() -> None:
    print(f"INFO: Listening on: {config.ip_address}:{config.port}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((config.ip_address, config.port))

    server.listen(1)

    connection_handler = ConnectionHandler()

    while True:
        conn, _ = server.accept()
        print("INFO: Client connected ")
        connection_handler.handle_connection(conn)


if __name__ == "__main__":
    main()
