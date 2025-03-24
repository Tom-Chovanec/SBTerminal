from datetime import datetime, timezone, timedelta

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


class MessageGenerator:
    @staticmethod
    def getIdleMessage(
        merchant_transaction_id: int,
        zr_number: int,
        device_number: int,
        device_type: int,
        terminal_id: str
    ) -> dict:
        utc_offset = timedelta(hours=1)
        now = datetime.now(timezone.utc) + utc_offset
        date_str = now.strftime('%d%m%y')
        time_str = now.strftime('%H%M%S')
        time_offset_str = f"UTC+{utc_offset.total_seconds() // 3600:.0f}"
        return {
            "TerminalStatusEMV": {
                'MerchantTransactionID': merchant_transaction_id,
                'ZRNumber': zr_number,
                'DeviceNumber': device_number,
                'DeviceType': device_type,
                'TerminalID': terminal_id,
                'Date': date_str,
                'Time': time_str,
                'TimeOffset': time_offset_str,
                'VersionProtocol': '1.25',
                'VersionEMVFirmware': '123_10Q',
                'ResponseStatus': 'STATUS',
                'ResponseCode': '100',
                'ResponseTextMessage': 'Idle',
            }
        }

    @staticmethod
    def getCardInMessage(
        merchant_transaction_id: int,
        zr_number: int,
        device_number: int,
        device_type: int,
        terminal_id: str
    ) -> dict:
        return {
            'TerminalStatusEMV': {
                'MerchantTransactionID': merchant_transaction_id,
                'ZRNumber': zr_number,
                'DeviceNumber': device_number,
                'DeviceType': device_type,
                'TerminalID': terminal_id,
                'ResponseStatus': 'STATUS',
                'ResponseCode': '101',
                'ResponseTextMessage': 'Card inserted',
            }
        }
