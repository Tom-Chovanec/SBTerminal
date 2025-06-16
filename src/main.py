import socket
import xml.etree.ElementTree as ET
import threading

from enum import Enum
from xml_parser import XMLParser
from terminal_config import load_config
from message_generator import CardIssuerCode, MessageGenerator, DefaultTags, TerminalStatusResponseCode, TransactionResponseCode, CardType, TerminalMessageResponseCode
from ui import MainWindow

from PySide6.QtCore import QThread, Signal, QObject, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QAbstractSocket, QTcpServer, QHostAddress, QTcpSocket

from logger import log_event
#ging

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
        log_event("ConnectionHandler initialized", TerminalStatusResponseCode.INITIALIZATION_PROCESSING, "info")  

    def sendXML(self, xml: str):
        padded_xml: str = f"\x02\n{xml}\x03"
        if self.conn:
            self.conn.write(padded_xml.encode())
            log_event("Sent XML", TerminalMessageResponseCode.INFO, "info")
        else:
            print("ERROR: No connected socket")
            log_event("No connected socket", TerminalStatusResponseCode.TERMINAL_UNAVAILABLE, "error")

    def send_idle_message_timed(self):
        idle_message_dict = MessageGenerator.get_terminal_status_emv_message(
            default_tags=default_tags,
            status_code=TerminalStatusResponseCode.IDLE
        )

        idle_message = XMLParser.dict_to_xml(idle_message_dict)

        if self.conn is not None:
            self.sendXML(idle_message)
            print("INFO: Sent idle message")
            log_event("Sent idle message", TerminalStatusResponseCode.IDLE, "info")
        else:
            print("ERROR: No connection")
            log_event("No connection", TerminalStatusResponseCode.TERMINAL_UNAVAILABLE, "error")

    def start_idle_message_timer(self, timeout: int):
        self.stop_idle_message_timer()  # Stop any existing timer

        if timeout > 0:
            self.idle_message_timer.timeout.connect(
                self.send_idle_message_timed)
            self.idle_message_timer.start((timeout - 2) * 1000)
            print(f"INFO: Idle message timer started with interval {timeout - 2} seconds")
            log_event(f"Idle message timer started with interval {timeout - 2} seconds", TerminalStatusResponseCode.IDLE, "info")  
        else:
            print("WARN: Timeout is 0, idle message timer not started.")
            log_event("Timeout is 0, idle message timer not started.", TerminalStatusResponseCode.TERMINAL_IS_BUSY, "warning")  

    def stop_idle_message_timer(self):
        if self.idle_message_timer.isActive():
            self.idle_message_timer.stop()
            try:
                self.idle_message_timer.timeout.disconnect(
                    self.send_idle_message_timed)
                log_event("Idle message timer stopped", TerminalStatusResponseCode.IDLE, "info")  
            except TypeError:
                pass
            print("INFO: Idle message timer stopped")
            log_event("Idle message timer stopped", TerminalStatusResponseCode.IDLE, "info")  

    def send_payment(self, card_details: dict):
        global price, currency_code
        print("send payment")
        log_event(f"Processing payment for card ending {card_details.get('card_number', '')[-4:]}", TerminalStatusResponseCode.AUTHORIZATION_PROCESSING, "info")  

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
            log_event("Sent transaction response", TerminalStatusResponseCode.AUTHORIZATION_APPROVED, "info")  
        else:
            print("ERROR: No connection")
            log_event("No connection when sending payment", TerminalStatusResponseCode.TERMINAL_UNAVAILABLE, "error")  

    def handle_connection(self, conn: QTcpSocket):
        self.conn = conn

        self.client_connected.emit()
        log_event("Client connected", TerminalStatusResponseCode.IDLE, "info")  

        if self.conn:
            self.conn.readyRead.connect(self.read_data)
            self.conn.disconnected.connect(self.on_client_disconnected)
        else:
            print("ERROR: No conn")
            log_event("No QTcpSocket object on handle_connection", TerminalStatusResponseCode.TERMINAL_UNAVAILABLE, "error")  

    def read_data(self):
        global price, currency_code
        data = self.conn.readAll()

        print("INFO: Received data")
        log_event("Received data from client", TerminalStatusResponseCode.IDLE, "info")  

        xml_cleaned = clean_xml(data.data().decode())
        parsed_xml = XMLParser.parse(xml_cleaned)
        log_event(f"Parsed XML: {xml_cleaned}", TerminalStatusResponseCode.IDLE, "debug")  

        if config.send_rsp_before_timeout:
            timeout_value = XMLParser.get_value(
                parsed_xml, "TimeoutResponse", 0)
            timeout = int(
                timeout_value) if timeout_value is not None else 0

            if timeout != 0:
                print(f'INFO: Setting timeout interval to "{timeout}"')
                log_event(f'Setting timeout interval to "{timeout}"', TerminalStatusResponseCode.IDLE, "info")  
                self.start_idle_message_timer(timeout)
            else:
                print('WARN: Timeout is "0"')
                log_event('Timeout is "0"', TerminalStatusResponseCode.TERMINAL_IS_BUSY, "warning")  

        price = XMLParser.get_value(
            parsed_xml, 'TransactionAmount', '0.00')
        currency_code = XMLParser.get_value(
            parsed_xml, 'CurrencyCode', '')

        log_event(f"Price updated: {price} {currency_code}", TerminalStatusResponseCode.IDLE, "info")  
        self.price_updated.emit(f"{price} {currency_code}")

    def on_client_disconnected(self):
        print("INFO: Client disconnected")
        log_event("Client disconnected", TerminalStatusResponseCode.CARD_REMOVED, "info")  
        self.stop_idle_message_timer()
        self.client_disconnected.emit()
        self.conn = None


def clean_xml(xml: str) -> str:
    cleaned = xml.strip("\x02\x03")
    log_event(f"Cleaned XML: {cleaned}", TerminalStatusResponseCode.IDLE, "debug")  
    return cleaned


class ServerThread(QThread):
    def __init__(self, ip, port, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.port = port
        self.connection_handler = ConnectionHandler()
        self.connection_handler.moveToThread(self)
        self.conn = None
        log_event(f"ServerThread initialized on {ip}:{port}", TerminalStatusResponseCode.INITIALIZATION_PROCESSING, "info")  

    def run(self):
        self.server_socket = QTcpServer()
        if not self.server_socket.listen(QHostAddress(self.ip), self.port):
            print(f"ERROR: Could not start server: {self.server_socket.errorString()}")
            log_event(f"Could not start server: {self.server_socket.errorString()}", TerminalStatusResponseCode.TERMINAL_UNAVAILABLE, "error")  
            return

        print(f"INFO: Listening on: {self.ip}:{self.port}")
        log_event(f"Listening on: {self.ip}:{self.port}", TerminalStatusResponseCode.IDLE, "info")  

        self.server_socket.newConnection.connect(self.on_new_connection)

        self.exec()

    def on_new_connection(self):
        print("INFO: Client connected")
        log_event("New client connection", TerminalStatusResponseCode.IDLE, "info")  
        conn = self.server_socket.nextPendingConnection()
        self.connection_handler.handle_connection(conn)

    def stop(self):
        if hasattr(self, 'server_socket') and self.server_socket:
            self.server_socket.close()
            log_event("Server socket closed", TerminalStatusResponseCode.DEACTIVATION_PROCESSING, "info")  
        self.quit()
        self.wait()
        log_event("Server thread stopped", TerminalStatusResponseCode.DEACTIVATION_PROCESSING, "info")  


def main() -> None:
    log_event("Application starting", TerminalStatusResponseCode.INITIALIZATION_PROCESSING, "info")  
    app = QApplication([])

    window = MainWindow()
    log_event("MainWindow initialized", TerminalStatusResponseCode.INITIALIZATION_PROCESSING, "info")
    server_thread = ServerThread(config.ip_address, config.port, window)

    server_thread.connection_handler.price_updated.connect(
        window.showPaymentScreen)
    server_thread.connection_handler.client_disconnected.connect(
        window.showIdleScreen)

    window.pay_button_clicked.connect(
        server_thread.connection_handler.send_payment)

    server_thread.start()
    window.show()
    log_event("Main window shown, server thread started", TerminalStatusResponseCode.INITIALIZATION_PROCESSING, "info")  

    app.exec()
    server_thread.stop()
    log_event("Application exited", TerminalStatusResponseCode.DEACTIVATION_PROCESSING, "info")  


if __name__ == "__main__":
    main()