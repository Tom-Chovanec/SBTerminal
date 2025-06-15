from PySide6.QtCore import QThread, Signal, QObject, QTimer, Slot
from PySide6.QtNetwork import QAbstractSocket, QTcpServer, QHostAddress, QTcpSocket
import time

from xml_parser import XMLParser
from terminal_config import config
from message_generator import CardIssuerCode, MessageGenerator, DefaultTags, TerminalMessageResponseCode, TerminalStatusResponseCode, TransactionResponseCode, CardType, DisplayMessageLevel, TransactionCancelCode

price: str
currency_code: str

default_tags: DefaultTags


class ConnectionHandler(QObject):
    price_updated = Signal(str)
    client_connected = Signal()
    client_disconnected = Signal()

    def __init__(self):
        super().__init__()
        self.is_stopping = False
        self.conn: QTcpSocket | None = None
        self.idle_message_timer = QTimer(self)

    def sendXML(self, xml: str):
        if self.is_stopping or not self.conn:
            if not self.is_stopping:
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

    @Slot(TerminalStatusResponseCode)
    def recieve_status_from_ui(self, status_code: TerminalStatusResponseCode):
        self.send_status(status_code)

    @Slot(str, int, DisplayMessageLevel)
    def recieve_display_from_ui(self, text: str, message_code: int, message_level: DisplayMessageLevel):
        self.send_display_message(text, message_code, message_level)

    @Slot(TransactionResponseCode, dict)
    def recieve_transaction_response_from_ui(self, response_code: TransactionResponseCode, card_details: dict):
        if card_details != {}:
            self.send_transaction_response(response_code, card_details)
        else:
            self.send_transaction_response(response_code)

    def send_status(self, status_code: TerminalStatusResponseCode):
        print(f"INFO: Sent status: {status_code}")
        status_response_dict = MessageGenerator.get_terminal_status_emv_message(
            default_tags=default_tags,
            status_code=status_code
        )

        status_response = XMLParser.dict_to_xml(status_response_dict)

        if self.conn is not None:
            self.sendXML(status_response)
            print("INFO: Sent transaction response")
        else:
            print("ERROR: No connection")

    def send_display_message(self, text: str, message_code: int, message_level: DisplayMessageLevel):
        print(f"INFO: Sent display message: {text}")
        display_message_response_dict = MessageGenerator.get_terminal_display_emv_message(
            default_tags=default_tags,
            display_message=text,
            display_message_code=message_code,
            display_message_level=message_level,
            language_code="en"
        )

        display_message_response = XMLParser.dict_to_xml(
            display_message_response_dict)

        if self.conn is not None:
            self.sendXML(display_message_response)
            print("INFO: Sent transaction response")
        else:
            print("ERROR: No connection")

    def send_transaction_response(self, response_code: TransactionResponseCode, card_details: dict = {}):
        print(f"Sent transaction response: {response_code}")
        if card_details != {}:
            transaction_response_dict = MessageGenerator.get_transaction_emv_response_message(
                default_tags=default_tags,
                response_code=response_code,
                account_number=card_details["card_number"],
                expiration_date=card_details["expiration_date"],
                card_issuer=card_details["card_issuer"],
                card_type=CardType.CHIP,
                original_transaction_amount=float(price),
                currency_code=currency_code
            )
        else:
            transaction_response_dict = MessageGenerator.get_transaction_emv_response_message(
                default_tags=default_tags,
                response_code=response_code
            )
        transaction_response = XMLParser.dict_to_xml(transaction_response_dict)

        if self.conn is not None:
            self.sendXML(transaction_response)
        else:
            print("ERROR: No connection")

    def send_payment(self, card_details: dict):
        global price, currency_code

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
            print("INFO: Sent payment")
        else:
            print("ERROR: No connection")

    def send_cancelation_approval(self):
        cancel_response_dict = MessageGenerator.get_transaction_emv_cancel_message(
            default_tags=default_tags,
            response_code=TransactionCancelCode.Cancel_accepted
        )

        cancel_response = XMLParser.dict_to_xml(cancel_response_dict)

        if self.conn is not None:
            self.sendXML(cancel_response)
            print("INFO: Sent cancellation approval")
        else:
            print("ERROR: No connection")

    def send_cancelation_response(self):
        cancel_response_dict = MessageGenerator.get_transaction_emv_response_message(
            default_tags=default_tags,
            response_code=TransactionResponseCode.Transaction_canceled_by_Merchant
        )

        cancel_response = XMLParser.dict_to_xml(cancel_response_dict)

        if self.conn is not None:
            self.sendXML(cancel_response)
            print("INFO: Sent cancellation")
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
        if self.conn is None:
            print("ERROR: No conn")
            return

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

        if XMLParser.get_value(parsed_xml, "TransactionEMV"):
            price = XMLParser.get_value(
                parsed_xml, 'TransactionAmount', '0.00')
            currency_code = XMLParser.get_value(parsed_xml, 'CurrencyCode', '')
            global default_tags
            default_tags = DefaultTags(
                merchant_transaction_id=XMLParser.get_value(
                    parsed_xml, 'MerchantTransactionID', 0),
                zr_number=XMLParser.get_value(parsed_xml, 'ZRNumber', 0),
                device_number=XMLParser.get_value(
                    parsed_xml, 'DeviceNumber', 0),
                device_type=XMLParser.get_value(parsed_xml, 'DeviceType', 0),
                terminal_id=XMLParser.get_value(parsed_xml, 'TerminalID', 0),
            )
        elif XMLParser.get_value(parsed_xml, "TransactionCancelEMV"):
            self.send_cancelation_approval()
            time.sleep(0.2)
            self.send_cancelation_response()

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
    def __init__(self, port, parent=None):
        super().__init__(parent)
        self.port = port
        self.connection_handler = ConnectionHandler()
        self.connection_handler.moveToThread(self)
        self.conn = None
        self.is_stopping = False

    def run(self):
        self.server_socket = QTcpServer()
        if not self.server_socket.listen(QHostAddress(QHostAddress.SpecialAddress.Any), self.port):
            print(f"ERROR: Could not start server: {
                  self.server_socket.errorString()}")
            return

        print(f"INFO: Listening on: {self.port}")

        self.server_socket.newConnection.connect(self.on_new_connection)

        self.exec()

        print("INFO: Server thread event loop exited")
        if self.connection_handler:
            self.connection_handler.shutdown()
        if self.server_socket:
            print(f"INFO: Server on socket: {self.port} closed")
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
