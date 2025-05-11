import socket
import xml.etree.ElementTree as ET
import threading

from xml_parser import XMLParser
from terminal_config import load_config
from message_generator import CardIssuerCode, MessageGenerator, DefaultTags, TerminalStatusResponseCode, TransactionResponseCode, CardType
from ui import MainWindow

from PySide6.QtCore import QThread, Signal, QObject
from PySide6.QtWidgets import QApplication

price: str = ''

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


class ConnectionHandler(QObject):
    price_updated = Signal(str)
    client_connected = Signal()
    client_disconnected = Signal()

    def __init__(self):
        super().__init__()
        self.idle_message_event = threading.Event()
        self.idle_message_thread = None
        self.running = True

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
        global price
        while self.running:
            data = conn.recv(4096)
            if not data:
                self.kill_idle_message_thread()
                self.client_disconnected.emit()
                break

            print("INFO: Received data")

            xml_cleaned = clean_xml(data.decode())
            parsed_xml = XMLParser.parse(xml_cleaned)

            if config.send_rsp_before_timeout:
                timeout_value = XMLParser.get_value(
                    parsed_xml, "TimeoutResponse", 0)
                timeout = int(
                    timeout_value) if timeout_value is not None else 0

                self.kill_idle_message_thread()

                if timeout != 0:
                    print(f'INFO: Setting timeout interval to "{timeout}"')
                    self.idle_message_event.clear()
                    self.idle_message_thread = threading.Thread(
                        target=self.send_idle_message, args=(conn, timeout))
                    self.idle_message_thread.start()
                else:
                    print('WARN: Timeout is "0"')

            price = XMLParser.get_value(
                parsed_xml, 'TransactionAmount', '0.00')
            price += ' '
            price += XMLParser.get_value(
                parsed_xml, 'CurrencyCode', '')

            self.price_updated.emit(price)


def clean_xml(xml: str) -> str:
    return xml.strip("\x02\x03")


class ServerThread(QThread):
    def __init__(self, ip, port, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.port = port
        self.connection_handler = ConnectionHandler()
        self.connection_handler.moveToThread(self)
        self.server_socket = None
        self.conn = None

    def run(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip, self.port))
        self.server_socket.listen(1)
        print(f"INFO: Listening on: {self.ip}:{self.port}")

        while True:
            conn, _ = self.server_socket.accept()
            self.conn = conn
            print("INFO: Client connected")
            self.connection_handler.handle_connection(self.conn)

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


def main() -> None:
    app = QApplication([])

    window = MainWindow()
    window.show()

    server_thread = ServerThread(config.ip_address, config.port, window)
    server_thread.connection_handler.price_updated.connect(
        window.showPaymentScreen)
    server_thread.connection_handler.client_disconnected.connect(
        window.showIdleScreen)

    server_thread.start()

    app.exec()
    server_thread.stop()


if __name__ == "__main__":
    main()
