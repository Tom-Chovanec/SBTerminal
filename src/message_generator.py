from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum

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


@dataclass
class DefaultTags:
    merchant_transaction_id: int
    zr_number: int
    device_number: int
    device_type: int
    terminal_id: str


class TerminalStatusResponseCode(Enum):
    IDLE = 100
    CARD_INSERTED = 101
    CARD_REMOVED = 102
    CHIP_CARD_ACCEPTED = 103
    SWIPED_CARD_ACCEPTED = 104
    CONTACTLESS_CARD_ACCEPTED = 105
    CARD_IDENTIFICATION = 106
    CARD_NOT_ACCEPTED = 107
    ENTER_PIN = 108
    PIN_ACCEPTED = 109
    WRONG_PIN = 110
    AUTHORIZATION_PROCESSING = 111
    AUTHORIZATION_APPROVED = 112
    AUTHORIZATION_DECLINED = 113
    INSERT_CARD = 114
    VOID_PROCESSING = 115
    INITIALIZATION_PROCESSING = 116
    SHIFT_CLOSE_PROCESSING = 117
    ACTIVATION_PROCESSING = 118
    DEACTIVATION_PROCESSING = 119
    DOWNLOAD_PROCESSING = 120
    TOP_UP_PROCESSING = 121
    REFUND_PROCESSING = 122

    # error status
    TERMINAL_IS_ERROR = 195
    TERMINAL_IS_DEACTIVATED = 196
    TERMINAL_IS_BUSY = 197
    TERMINAL_NOT_CONFIGURED = 198
    TERMINAL_UNAVAILABLE = 199
    FAULT_REQUEST = 999


class TerminalMessageResponseCode(Enum):
    EVENT = 800
    ALARM = 801
    JOURNAL = 802
    INFO = 803


class DisplayMessageLevel(Enum):
    INFO = 0
    ERROR = 1


class MessageGenerator:
    @staticmethod
    def get_terminal_status_emv_message(
        default_tags: DefaultTags,
        status_code: TerminalStatusResponseCode
    ) -> dict:
        utc_offset = timedelta(hours=1)
        now = datetime.now(timezone.utc) + utc_offset
        date_str = now.strftime('%d%m%y')
        time_str = now.strftime('%H%M%S')
        time_offset_str = f"UTC+{utc_offset.total_seconds() // 3600:.0f}"
        return {
            'TerminalStatusEMV': {
                # default tags
                'MerchantTransactionID': default_tags.merchant_transaction_id,
                'ZRNumber': default_tags.zr_number,
                'DeviceNumber': default_tags.device_number,
                'DeviceType': default_tags.device_type,
                'TerminalID': default_tags.terminal_id,

                # time tags
                'Date': date_str,
                'Time': time_str,
                'TimeOffset': time_offset_str,

                # version tags
                'VersionProtocol': '1.25',
                'VersionEMVFirmware': '123_10Q',

                # result tags
                'ResponseStatus': 'STATUS' if status_code.value < 190 else 'ERROR',
                'ResponseCode': status_code.value,
                'ResponseTextMessage': status_code._name_.replace("_", " ").title(),
            }
        }

    @staticmethod
    def get_terminal_message_emv_message(
        default_tags: DefaultTags,
        response_code: TerminalMessageResponseCode,
        response_text: str
    ) -> dict:
        return {
            'TerminalStatusEMV': {
                # default tags
                'MerchantTransactionID': default_tags.merchant_transaction_id,
                'ZRNumber': default_tags.zr_number,
                'DeviceNumber': default_tags.device_number,
                'DeviceType': default_tags.device_type,
                'TerminalID': default_tags.terminal_id,

                # result tags
                'ResponseStatus': 'MESSAGE',
                'ResponseCode': response_code.value,
                'ResponseTextMessage': response_text
            }
        }

    @staticmethod
    def get_terminal_display_emv_message(
        default_tags: DefaultTags,
        display_message: str,
        display_message_code: int,
        display_message_level: DisplayMessageLevel,
        language_code: str
    ) -> dict:
        return {
            'TerminalStatusEMV': {
                # default tags
                'MerchantTransactionID': default_tags.merchant_transaction_id,
                'ZRNumber': default_tags.zr_number,
                'DeviceNumber': default_tags.device_number,
                'DeviceType': default_tags.device_type,
                'TerminalID': default_tags.terminal_id,

                # Terminal Display message tag
                'DisplayMessage': display_message,
                'DisplayMessageCode': display_message_code,
                'DisplayMessageLevel': display_message_level.name,
                'LanguageCode': language_code
            }
        }
