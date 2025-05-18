from PySide6.QtCore import QThread, Signal, QObject, QTimer
from PySide6.QtNetwork import QAbstractSocket, QTcpServer, QHostAddress, QTcpSocket

from xml_parser import XMLParser
from terminal_config import config
from message_generator import CardIssuerCode, MessageGenerator, DefaultTags, TerminalStatusResponseCode, TransactionResponseCode, CardType

price: str
currency_code: str

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
        self.is_stopping = False
        self.conn: QTcpSocket = None
        self.idle_message_timer = QTimer(self)

    def sendXML(self, xml: str):
        if self.is_stopping or not self.conn:
            if not self.is_stopping:  # Only print error if not stopping
                print(
                    "ERROR: Cannot send XML, no connected socket or handler is stopping")
            return

        padded_xml: str = f"\x02\n{xml}\x03"
        self.conn.write(padded_xml.encode())

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
        if self.is_stopping:
            print("INFO: Not starting idle message timer, handler is stopping")
            return

        self.stop_idle_message_timer()

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

        xml_cleaned = self.clean_xml(data.data().decode())
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

    def shutdown(self):
        print("INFO: ConnectionHandler shutdown initiated")
        self.is_stopping = True
        if self.conn:
            self.conn.close()
            self.conn.deleteLater()
        self.conn = None

    def on_client_disconnected(self):
        print("INFO: Client disconnected")
        self.stop_idle_message_timer()
        self.client_disconnected.emit()
        self.conn = None

    def clean_xml(self, xml: str) -> str:
        return xml.strip("\x02\x03")


class ServerThread(QThread):
    def __init__(self, ip, port, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.port = port
        self.connection_handler = ConnectionHandler()
        self.connection_handler.moveToThread(self)
        self.conn = None
        self.is_stopping = False

    def run(self):
        self.server_socket = QTcpServer()
        if not self.server_socket.listen(QHostAddress(self.ip), self.port):
            print(f"ERROR: Could not start server: {
                  self.server_socket.errorString()}")
            # Consider emitting an error signal back to MainWindow
            return

        print(f"INFO: Listening on: {self.ip}:{self.port}")

        self.server_socket.newConnection.connect(self.on_new_connection)

        # Start the event loop
        self.exec()

        # After the event loop exits, ensure clean shutdown
        print("INFO: Server thread event loop exited")
        # Disconnect connections in ConnectionHandler if necessary
        if self.connection_handler:
            # Add a method to ConnectionHandler to handle clean shutdown
            self.connection_handler.shutdown()
        if self.server_socket:
            print(f"INFO: socket {self.ip}:{self.port} closed")
            self.server_socket.close()

    def on_new_connection(self):
        if self.is_stopping:
            return

        print("INFO: Client connected")
        conn = self.server_socket.nextPendingConnection()
        self.connection_handler.handle_connection(conn)

    def stop(self):
        print("INFO: Server thread stopped")
        self.is_stopping = True

        try:
            if self.connection_handler:
                self.connection_handler.price_updated.disconnect()
                self.connection_handler.client_disconnected.disconnect()
        except TypeError:
            pass

        self.quit()
        self.wait()
        print("INFO: Server thread stopped")
