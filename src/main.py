import socket
import xml.etree.ElementTree as ET
import threading
import xml.dom.minidom

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


class XMLParser:
    @staticmethod
    def parse(xml_string: str) -> dict:
        try:
            root = ET.fromstring(xml_string)
            return XMLParser._element_to_dict(root)
        except ET.ParseError as e:
            print(f"ERROR: Failed to parse XML - {e}")
            return {}

    @staticmethod
    def _element_to_dict(element: ET.Element) -> dict:
        parsed_data = {
            element.tag: {} if list(element)
            else element.text.strip() if element.text and element.text.strip()
            else ""
        }
        for child in element:
            if isinstance(parsed_data[element.tag], dict):
                parsed_data[element.tag].update(
                    XMLParser._element_to_dict(child))
            else:
                parsed_data[element.tag] = XMLParser._element_to_dict(child)
        return parsed_data

    @staticmethod
    def dict_to_xml(data: dict) -> str:
        def build_xml(element_name, value):
            element = ET.Element(element_name)
            if isinstance(value, dict):
                for k, v in value.items():
                    element.append(build_xml(k, v))
            else:
                element.text = str(value)
            return element

        if not isinstance(data, dict) or len(data) != 1:
            raise ValueError(
                "Input dictionary must have exactly one root element.")

        root_name, root_value = next(iter(data.items()))
        root_element = build_xml(root_name, root_value)

        raw_xml = ET.tostring(root_element, encoding="utf-8")
        parsed_xml = xml.dom.minidom.parseString(raw_xml)
        return parsed_xml.toprettyxml(indent="  ")


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
                timeout = int(parsed_xml.get("TransactionEMV",
                                             {}).get("TimeoutResponse", 0))

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
