import socket
import xml.etree.ElementTree as ET
import threading
import xml.dom.minidom

from terminal_config import load_config

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

card_in_message: str = """
\x02
<?xml version="1.0" ?>
<TerminalStatusEMV>
<MerchantTransactionID>12345</MerchantTransactionID>
<ZRNumber>2010</ZRNumber>
<DeviceNumber>601</DeviceNumber>
<DeviceType>6</DeviceType>
<TerminalID>Term01</TerminalID>
<ResponseStatus>STATUS</ResponseStatus>
<ResponseCode>101</ResponseCode>
<ResponseTextMessage>Card inserted</ResponseTextMessage>
</TerminalStatusEMV>
\x03
"""

approved_message: str = """
\x02
<?xml version="1.0"?>
<TransactionEMV>
<AccountNumber>***********2345</AccountNumber>
<HashedEpan>437BF2A684A75C61DFABCD</HashedEpan>
<ApprovalCode>ABC12345678901234567</ApprovalCode>
<ExpirationDate>0512</ExpirationDate>
<CardIssuer>MC</CardIssuer>
<CardType>CHIP</CardType>
<MerchantTransactionID>12345</MerchantTransactionID>
<ZRNumber>2010</ZRNumber>
<DeviceNumber>601</DeviceNumber>
<DeviceType>6</DeviceType>
<TerminalID>Term01</TerminalID>
<ResponseStatus>AUTHORIZED</ResponseStatus>
<ResponseCode>000</ResponseCode>
<ResponseTextMessage>APPROVAL 090882</ResponseTextMessage>
<TransactionAmount>0.50</TransactionAmount>
<CurrecyCode>CAD</CurrecyCode>
<TransactionDate>130828</TransactionDate>
<TransactionTime>142303</TransactionTime>
<TransactionIdentifier>12345678901234567890</TransactionIdentifier>
<BatchID>123456</BatchID>
<CustomerReceipt>MID: ***33932
TID: ****4236
AID: 0000000031010
MASTERCARD DEBIT
PAN SEQ NO: 00
ICC
SALE
AMOUNT CAD2.50
PIN VERIFIED
AUTH CODE:090882
18/04/14 00:06
RETAIN FOR YOUR RECORDS
THANK YOU
</CustomerReceipt>
<MerchantReceipt> MID: ***33932
TID: ****4236
AID: 0000000031010
MASTERCARD DEBIT
PAN SEQ NO: 00
ICC
SALE
AMOUNT CAD2.50
PIN VERIFIED
AUTH CODE: 090882
18/04/14 00:06
RETAIN FOR YOUR RECORDS
THANK YOU
</MerchantReceipt>
</TransactionEMV>
\x03
"""

config = load_config()


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
        parsed_data = {element.tag: {} if list(element) else element.text.strip() if element.text and element.text.strip() else ""}
        for child in element:
            if isinstance(parsed_data[element.tag], dict):  
                parsed_data[element.tag].update(XMLParser._element_to_dict(child))
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
            raise ValueError("Input dictionary must have exactly one root element.")
        
        root_name, root_value = next(iter(data.items()))
        root_element = build_xml(root_name, root_value)
        
        raw_xml = ET.tostring(root_element, encoding="utf-8")
        parsed_xml = xml.dom.minidom.parseString(raw_xml)
        return parsed_xml.toprettyxml(indent="  ")


class ConnectionHandler:
    def __init__(self):
        self.idle_message_event = threading.Event()
        self.idle_message_thread = None

    def send_idle_message(self, conn: socket.socket, timeout: int):
        self.idle_message_event.clear()
        while not self.idle_message_event.wait(timeout - 2):
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

            xml_cleaned = clean_xml(data.decode())
            parsed_xml = XMLParser.parse(xml_cleaned)

            if config.send_rsp_before_timeout:
                # this should probably be reworked
                timeout = int(parsed_xml.get("TransactionEMV", {}).get("TimeoutResponse", 0))

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

            # if "TransactionEMV" in parsed_xml:
            #     time.sleep(2)
            #     conn.sendall(card_in_message.encode())
            #     print("INFO: Sent card in message")
            #     time.sleep(2)
            #     conn.sendall(approved_message.encode())
            #     print("INFO: Sent payment approved message")



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
