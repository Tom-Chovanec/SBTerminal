import socket
import xml.etree.ElementTree as ET
import threading

from xml_parser import XMLParser
from terminal_config import load_config
from message_generator import CardIssuerCode, MessageGenerator, DefaultTags, TerminalStatusResponseCode, TransactionResponseCode, CardType
from ui import MainWindow

from PySide6.QtCore import QThread, Signal, QObject, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QAbstractSocket, QTcpServer, QHostAddress, QTcpSocket

price: str
currency_code: str

config = load_config()
default_tags = DefaultTags(
    merchant_transaction_id=2,
    zr_number=2055,
    device_number=601,
    device_type=6,
    terminal_id='Term01'
)


class ConnectionHandler(QObject):
    price_updated = Signal(str)
    client_connected = Signal()
    client_disconnected = Signal()

    def __init__(self):
        super().__init__()
        self.running = True
        self.conn: QTcpSocket
        self.idle_message_timer = QTimer(self)

    def sendXML(self, xml: str):
        padded_xml: str = f"\x02\n{xml}\x03"
        if self.conn:
            self.conn.write(padded_xml.encode())
        else:
            print("ERROR: No connected socket")

    def send_idle_message_timed(self):
        idle_message_dict = MessageGenerator.get_terminal_status_emv_message(
            default_tags=default_tags,
            status_code=TerminalStatusResponseCode.IDLE
        )

        idle_message = XMLParser.dict_to_xml(idle_message_dict)

        if self.conn is not None:
            self.sendXML(idle_message)
            print("INFO: Sent idle message")
        else:
            print("ERROR: No connection")

    def start_idle_message_timer(self, timeout: int):
        self.stop_idle_message_timer()  # Stop any existing timer

        if timeout > 0:
            self.idle_message_timer.timeout.connect(
                self.send_idle_message_timed)
            self.idle_message_timer.start((timeout - 2) * 1000)
            print(f"INFO: Idle message timer started with interval {
                  timeout - 2} seconds")
        else:
            print("WARN: Timeout is 0, idle message timer not started.")

    def stop_idle_message_timer(self):
        if self.idle_message_timer.isActive():
            self.idle_message_timer.stop()
            try:
                self.idle_message_timer.timeout.disconnect(
                    self.send_idle_message_timed)
            except TypeError:
                pass
            print("INFO: Idle message timer stopped")

    def send_payment(self, card_details: dict):
        global price, currency_code
        print("send payment")

        transaction_response_dict = MessageGenerator.get_transaction_emv_response_message(
            default_tags=default_tags,
            response_code=TransactionResponseCode.AUTHORISED,
            account_number=card_details["card_number"],
            expiration_date=card_details["expiration_date"],
            card_issuer=card_details["card_issuer"],
            card_type=CardType.CHIP,
            original_transaction_amount=float(price),
            currency_code=currency_code
        )

        transaction_response = XMLParser.dict_to_xml(transaction_response_dict)

        if self.conn is not None:
            self.sendXML(transaction_response)
            print("INFO: Sent transaction response")
        else:
            print("ERROR: No connection")

    def handle_connection(self, conn: QTcpSocket):
        self.conn = conn

        self.client_connected.emit()

        if self.conn:
            self.conn.readyRead.connect(self.read_data)
            self.conn.disconnected.connect(self.on_client_disconnected)
        else:
            print("ERROR: No conn")

    def read_data(self):
        global price, currency_code
        data = self.conn.readAll()

        print("INFO: Received data")

        xml_cleaned = clean_xml(data.data().decode())
        parsed_xml = XMLParser.parse(xml_cleaned)

        if config.send_rsp_before_timeout:
            timeout_value = XMLParser.get_value(
                parsed_xml, "TimeoutResponse", 0)
            timeout = int(
                timeout_value) if timeout_value is not None else 0

            if timeout != 0:
                print(f'INFO: Setting timeout interval to "{timeout}"')
                self.start_idle_message_timer(timeout)
            else:
                print('WARN: Timeout is "0"')

        price = XMLParser.get_value(
            parsed_xml, 'TransactionAmount', '0.00')
        currency_code = XMLParser.get_value(
            parsed_xml, 'CurrencyCode', '')

        self.price_updated.emit(f"{price} {currency_code}")

    def on_client_disconnected(self):
        print("INFO: Client disconnected")
        self.stop_idle_message_timer()
        self.client_disconnected.emit()
        self.conn = None


def clean_xml(xml: str) -> str:
    return xml.strip("\x02\x03")


class ServerThread(QThread):
    def __init__(self, ip, port, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.port = port
        self.connection_handler = ConnectionHandler()
        self.connection_handler.moveToThread(self)
        self.conn = None

    def run(self):
        self.server_socket = QTcpServer()
        if not self.server_socket.listen(QHostAddress(self.ip), self.port):
            print(f"ERROR: Could not start server: {
                  self.server_socket.errorString()}")
            return

        print(f"INFO: Listening on: {self.ip}:{self.port}")

        self.server_socket.newConnection.connect(self.on_new_connection)

        self.exec()

    def on_new_connection(self):
        print("INFO: Client connected")
        conn = self.server_socket.nextPendingConnection()
        self.connection_handler.handle_connection(conn)

    def stop(self):
        if self.server_socket:
            self.server_socket.close()
        self.quit()
        self.wait()


def main() -> None:
    app = QApplication([])

    window = MainWindow()
    server_thread = ServerThread(config.ip_address, config.port, window)

    server_thread.connection_handler.price_updated.connect(
        window.showPaymentScreen)
    server_thread.connection_handler.client_disconnected.connect(
        window.showIdleScreen)

    window.pay_button_clicked.connect(
        server_thread.connection_handler.send_payment)

    server_thread.start()
    window.show()

    app.exec()
    server_thread.stop()


if __name__ == "__main__":
    main()