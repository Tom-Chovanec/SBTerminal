from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
import string
import secrets
import random


@dataclass
class DefaultTags:
    merchant_transaction_id: int
    zr_number: int
    device_number: int
    device_type: int
    terminal_id: str


class AlphanumericEnum(str, Enum):
    def __str__(self):
        return self.value


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


class TerminalMessageResponseCode(AlphanumericEnum):
    EVENT = 800
    ALARM = 801
    JOURNAL = 802
    INFO = 803


class DisplayMessageLevel(AlphanumericEnum):
    INFO = 0
    ERROR = 1


class CardIssuerCode(AlphanumericEnum):
    XX = 'Unknown / Non-Payment / Loyalty'
    VS = 'Visa'
    MC = 'Master Card'
    CA = 'Master Card'
    DC = 'Diners Club'
    DN = 'Diners Club'
    IN = 'Interac Canada'
    AX = 'American Express'
    JC = 'JCB – Japan Credit Bureau'
    MA = 'Maestro'
    CU = 'China UnionPay'
    DS = 'Discover'


class CardType(Enum):
    MAGN = 'MAGN'  # magnetic stripe
    CHIP = 'CHIP'  # chipped card
    CLESS = 'CLESS'  # contactless card


class TransactionResponseCode(AlphanumericEnum):
    AUTHORISED = '000'
    REFERRED = '001'
    REFERRED_SPECIAL_CONDITIONS = '002'
    INVALID_MERCHANT = '003'
    HOLD_CARD = '004'
    REFUSED = '005'
    ERROR = '006'
    HOLD_CARD_SPECIAL_CONDITIONS = '007'
    APPROVE_AFTER_IDENTIFICATION = '008'
    APPROVED_FOR_PARTIAL_AMOUNT = '010'
    APPROVED_VIP = '011'
    INVALID_TRANSACTION = '012'
    INVALID_AMOUNT = '013'
    INVALID_ACCOUNT = '014'
    INVALID_CARD_ISSUER = '015'
    APPROVED_UPDATE_TRACK3 = '016'
    ANNULATION_BY_CLIENT = '017'
    CUSTOMER_DISPUTE = '018'
    RE_ENTER_TRANSACTION = '019'
    INVALID_RESPONSE = '020'
    NO_ACTION_TAKEN = '021'
    SUSPECTED_MALFUNCTION = '022'
    UNACCEPTABLE_TRANSACTION_FEE = '023'
    ACCESS_DENIED = '028'
    FORMAT_ERROR = '030'
    UNKNOWN_ACQUIRER_ACCOUNT = '031'
    CARD_EXPIRED = '033'
    FRAUD_SUSPICION = '034'
    SECURITY_CODE_EXPIRED = '038'
    FUNCTION_NOT_SUPPORTED = '040'
    LOST_CARD = '041'
    STOLEN_CARD = '043'
    LIMIT_EXCEEDED = '051'
    CARD_EXPIRED_PICK_UP = '054'
    INVALID_SECURITY_CODE = '055'
    UNKNOWN_CARD = '056'
    ILLEGAL_TRANSACTION = '057'
    TRANSACTION_NOT_PERMITTED = '058'
    RESTRICTED_CARD = '062'
    SECURITY_RULES_VIOLATED = '063'
    EXCEED_WITHDRAWAL_FREQUENCY = '065'
    TRANSACTION_TIMED_OUT = '068'
    EXCEED_PIN_TRIES = '075'
    INVALID_DEBIT_ACCOUNT = '076'
    INVALID_CREDIT_ACCOUNT = '077'
    BLOCKED_FIRST_USED = '078'
    CREDIT_ISSUER_UNAVAILABLE = '080'
    PIN_CRYPROGRAPHIC_ERROR = '081'
    INCORRECT_CCV = '082'
    UNABLE_TO_VERIFY_PIN = '083'
    REJECTED_BY_CARD_ISSUER = '085'
    ISSUER_UNAVAILABLE = '091'
    ROUTING_ERROR = '092'
    TRANSACTION_CANNOT_COMPLETE = '093'
    DUPLICATE_TRANSACTION = '094'
    SYSTEM_ERROR = '096'
    OFFLINE_AUTHORISED = '0Y1'
    ISSUER_UNAVAILABLE_AUTHORISED = '0Y3'
    OFFLINE_REFUSED = '0Z1'
    ISSUER_UNAVAILABLE_REFUSED = '0Z3'
    Transaction_canceled_by_Merchant = '200'
    Transaction_canceled_by_terminal_user = '201'
    Transaction_canceled_after_exception = '202'
    Transaction_canceled_after_removed_card = '203'
    Terminal_is_deactivated = '296'
    Terminal_is_busy = '297'
    Terminal_not_configured = '298'
    Terminal_unavailable = '299'
    Fault_request = '999'


def getTransactionResponseStatusFromCode(
        transaction_response_code: str
) -> str:
    error = {'003', '006', '012', '014', '019', '020', '021', '022', '030',
             '031', '040', '058', '068', '080', '081', '083', '091', '092',
             '093', '096', '296', '297', '298', '299', '999'}
    authorized = {'000', '008', '010', '011', '016', '0Y1', '0Y3'}
    refused = {'001', '002', '004', '005', '007', '013', '015', '018', '023',
               '028', '033', '034', '038', '041', '043', '051', '054', '055',
               '056', '057', '062', '063', '065', '075', '076', '077', '078',
               '082', '085', '094', '0Z1', '0Z3'}
    canceled = {'017', '200', '201', '202', '203'}

    if transaction_response_code in error:
        return 'ERROR'
    elif transaction_response_code in authorized:
        return 'AUTHORIZED'
    elif transaction_response_code in refused:
        return 'REFUSED'
    elif transaction_response_code in canceled:
        return 'CANCELED'
    return 'INVALID_RESPONSED_CODE'


def generate_random_an_string(length=20):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


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
            'TerminalDisplayEMV': {
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

    @staticmethod
    def get_transaction_emv_response_message(
        default_tags: DefaultTags,
        response_code: TransactionResponseCode,
        account_number: str,
        # hashed_epan: str,
        expiration_date: str,
        card_issuer: CardIssuerCode,
        card_type: CardType,
        # unaltered_track_data: str = '',
        original_transaction_amount: float = 0.0,
        currency_code: str = '',
        surcharge_amount: float = 0.0,
        discount_amount: float = 0.0
    ) -> dict:
        utc_offset = timedelta(hours=1)
        now = datetime.now(timezone.utc) + utc_offset
        date_str = now.strftime('%d%m%y')
        time_str = now.strftime('%H%M%S')
        time_offset_str = f"UTC+{utc_offset.total_seconds() // 3600:.0f}"
        return {
            'TransactionEMV': {
                # default tags
                'MerchantTransactionID': default_tags.merchant_transaction_id,
                'ZRNumber': default_tags.zr_number,
                'DeviceNumber': default_tags.device_number,
                'DeviceType': default_tags.device_type,
                'TerminalID': default_tags.terminal_id,

                # card data tags
                # **({'UnalteredTrackData': unaltered_track_data}
                #    if unaltered_track_data != '' else {}),
                'AccountNumber': account_number,
                # 'HashedEpan': hashed_epan
                'ExpirationDate': expiration_date,
                'CardIssuer': card_issuer,
                'CardType': card_type.name,

                # result tags
                'ResponseStatus':
                    getTransactionResponseStatusFromCode(response_code.value),
                'ResponseCode': response_code,
                'ResponseTextMessage': response_code._name_.replace("_", " "),

                # transaction tags
                **({'OriginalTransactionAmount': original_transaction_amount}
                        if surcharge_amount != 0.0
                        or discount_amount != 0.0 else {}),
                'TransactionAmount': original_transaction_amount
                    + surcharge_amount - discount_amount,
                **({'SurchargeAmount': surcharge_amount}
                        if surcharge_amount != 0.0 else {}),
                **({'DiscountAmount': discount_amount}
                        if discount_amount != 0.0 else {}),
                # 'CardAmount': '0.00'
                'ApprovalCode': generate_random_an_string(20),
                'TransactionDate': date_str,
                'TransactionTime': time_str,
                'TransactionTimeOffset': time_offset_str,
                'TransactionIdentifier': random.randint(10**19, 10**20 - 1),
                # TODO: generate receipts
                'MerchantReceipt': 'asdasd',
                'CustomerReceipt': 'sadsad',
                'CurrencyCode': currency_code,
                'BarchID': generate_random_an_string(20)
            }
        }
