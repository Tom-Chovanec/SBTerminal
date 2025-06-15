import os
import time
from PySide6.QtGui import (
    QPainterPath,
    QPixmap,
    QFont,
    QColor,
    QPainter,
    QPen,
    QIntValidator,
)
from PySide6.QtCore import (
    QSize,
    Qt,
    QPointF,
    Signal,
)
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QCheckBox,
    QSpinBox,
    QPushButton,
    QGridLayout,
    QComboBox,
    QGroupBox,
    QLineEdit,
    QFormLayout,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
    QSpacerItem,
)

from message_generator import TerminalStatusResponseCode, DisplayMessageLevel, TransactionResponseCode
from terminal_config import config, save_config
from server import ServerThread


os.environ["QT_IM_MODULE"] = "qtvirtualkeyboard"

card_details: dict


def getImagePath(name: str) -> str:
    imagePath = f'assets/images/{name}'
    if not os.path.exists(imagePath):
        print(f"ERROR: {imagePath} not found")
        return ''
    return imagePath


class DiamondButton(QPushButton):
    def __init__(self, text: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = text

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        pen = QPen(QColor("white"), 4)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        corner_radius = 25.0
        cx, cy = w / 2, h / 2

        path = QPainterPath()

        # Start at top-right *straight section* before the corner
        path.moveTo(QPointF(cx + corner_radius, corner_radius))

        # Top-right curve
        path.quadTo(QPointF(cx, 0), QPointF(cx - corner_radius, corner_radius))

        # Left top to middle-left
        path.lineTo(QPointF(corner_radius, cy - corner_radius))
        path.quadTo(QPointF(0, cy), QPointF(corner_radius, cy + corner_radius))

        # Bottom-left to bottom-center
        path.lineTo(QPointF(cx - corner_radius, h - corner_radius))
        path.quadTo(QPointF(cx, h), QPointF(
            cx + corner_radius, h - corner_radius))

        # Bottom-right to middle-right
        path.lineTo(QPointF(w - corner_radius, cy + corner_radius))
        path.quadTo(QPointF(w, cy), QPointF(
            w - corner_radius, cy - corner_radius))

        # Back to top-right straight segment
        path.lineTo(QPointF(cx + corner_radius, corner_radius))

        painter.drawPath(path)

        # Draw the text
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Kulim Park", 25))
        painter.drawText(
            self.rect(), Qt.AlignmentFlag.AlignCenter, self.text)


class MainWindow(QMainWindow):
    pay_button_clicked = Signal(dict)
    send_status_signal = Signal(TerminalStatusResponseCode)
    send_display_message = Signal(str, int, DisplayMessageLevel)
    send_transaction_response = Signal(TransactionResponseCode, dict)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("SBTerminal")
        self.setFixedSize(QSize(480, 800))
        # self.setWindowState(Qt.WindowFullScreen)
        self.setStyleSheet("background-color: #181818;")

        self.server_thread: ServerThread | None = None
        # Set the initial screen
        self.showIdleScreen()

    def createIdleScreen(self):
        """Creates and returns the main idle screen."""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)

        logo_path = getImagePath('sb_logo.png')
        settings_image_path = getImagePath('settings.png')

        # settings button
        settings_button = QPushButton()
        settings_icon = QPixmap(settings_image_path)
        settings_button.clicked.connect(self.showSettingsScreen)

        settings_button.setIcon(settings_icon)
        settings_button.setIconSize(QSize(64, 64))
        settings_button.setFixedSize(64, 64)
        settings_button.setStyleSheet("border: none; background: none;")

        # logo label
        big_logo = QLabel()
        big_logo.setPixmap(QPixmap(logo_path).scaledToWidth(375))
        big_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(
            settings_button,
            0, 0,
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        layout.addWidget(big_logo, 0, 0, Qt.AlignmentFlag.AlignCenter)

        return widget

    def createSettingsScreen(self):
        """Creates and returns the settings screen with config-bound fields."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        widget.setStyleSheet("color: white;")

        # Back Button
        back_button_layout = QHBoxLayout()
        settings_image_path = getImagePath('back_arrow.png')
        back_button = QPushButton()
        settings_icon = QPixmap(settings_image_path)
        back_button.setIcon(settings_icon)
        back_button.setIconSize(QSize(64, 64))
        back_button.setFixedSize(64, 64)
        # Keep original style for button
        back_button.setStyleSheet("border: none; background: none;")
        back_button.clicked.connect(self.saveSettings)
        back_button.clicked.connect(self.showIdleScreen)
        back_button_layout.addWidget(
            back_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(back_button_layout)

        # Card Details
        card_group = QGroupBox("Card Details")
        # Explicitly set color for group box title
        card_group.setStyleSheet("QGroupBox { color: white; }")
        card_layout = QVBoxLayout()

        self.card_number_input_settings = QLineEdit(config.card_number)
        self.card_number_input_settings.setPlaceholderText("Card Number")
        card_layout.addWidget(self.card_number_input_settings)

        exp_layout = QHBoxLayout()
        self.exp_month_settings = QLineEdit(
            config.expiration_date[:2])
        self.exp_month_settings.setPlaceholderText("MM")
        self.exp_month_settings.setFixedWidth(50)
        exp_layout.addWidget(self.exp_month_settings)

        self.exp_year_settings = QLineEdit(
            config.expiration_date[2:])
        self.exp_year_settings.setPlaceholderText("YY")
        self.exp_year_settings.setFixedWidth(50)
        exp_layout.addWidget(self.exp_year_settings)

        self.cvv_input_settings = QLineEdit(config.cvv)
        self.cvv_input_settings.setPlaceholderText("CVV")
        self.cvv_input_settings.setFixedWidth(60)
        exp_layout.addWidget(self.cvv_input_settings)

        card_layout.addLayout(exp_layout)
        card_group.setLayout(card_layout)
        layout.addWidget(card_group)

        network_group = QGroupBox("Network Settings")

        network_group.setStyleSheet("QGroupBox { color: white; }")
        network_layout = QFormLayout()
        self.port_input = QLineEdit(str(config.port))
        self.port_input.setValidator(QIntValidator(1, 65535))
        network_layout.addRow("Port:", self.port_input)
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)

        # Toggle
        self.send_response_toggle = QCheckBox("Send Response")
        self.send_response_toggle.setChecked(config.send_rsp_before_timeout)
        layout.addWidget(self.send_response_toggle)

        layout.addStretch()

        return widget

    def createPaymentScreen(self, price_text_value: str):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)

        # Top layout with logo
        topLayout = QHBoxLayout()
        topLayout.addStretch()
        text_logo = QLabel()
        pixmap = QPixmap(getImagePath('text_logo.png'))
        text_logo.setPixmap(pixmap)
        text_logo.setFixedHeight(50)
        topLayout.addWidget(text_logo)
        layout.addLayout(topLayout, 0, 0)

        # Divider line
        divider = QLabel()
        divider.setFixedHeight(3)
        divider.setStyleSheet("background-color: white;")
        layout.addWidget(divider)
        # Main content
        mainContent = QVBoxLayout()
        mainContent.setSpacing(30)

        title = QLabel("Payment")
        title.setFont(QFont("Kulim Park", 50))
        title.setStyleSheet(
            "color: white; font-weight: semibold; margin-top: 50px;")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        mainContent.addWidget(title)

        price_text = QLabel(price_text_value)
        price_text.setFont(QFont("Kulim Park", 30))
        price_text.setStyleSheet(
            "color: white; font-weight: semibold; margin-left: 10px;")
        price_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
        mainContent.addWidget(price_text)

        mainContent.addSpacerItem(QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        button_layout = QHBoxLayout()
        # Diamond-shaped button
        manual_pay_button = DiamondButton("Manual\nPay")
        manual_pay_button.setFixedSize(200, 200)
        manual_pay_button.setStyleSheet(
            "background-color: transparent; border: none;")
        manual_pay_button.clicked.connect(self.showMessagesScreen)
        manual_pay_button.clicked.connect(self.handlePayButtonClicked)

        quick_pay_button = DiamondButton("Quick\npay")
        quick_pay_button.setFixedSize(200, 200)
        quick_pay_button.setStyleSheet(
            "background-color: transparent; border: none;")
        quick_pay_button.clicked.connect(self.handleQuickPayButtonClicked)

        simulated_pay_button = DiamondButton("Simulated\nPay")
        simulated_pay_button.setFixedSize(200, 200)
        simulated_pay_button.setStyleSheet(
            "background-color: transparent; border: none;")
        simulated_pay_button.clicked.connect(
            self.handleSimulatedPayButtonClicked)

        button_layout.addWidget(
            manual_pay_button, alignment=Qt.AlignmentFlag.AlignCenter)

        button_layout.addWidget(
            simulated_pay_button, alignment=Qt.AlignmentFlag.AlignCenter)

        mainContent.addLayout(button_layout)
        mainContent.addWidget(
            quick_pay_button, alignment=Qt.AlignmentFlag.AlignCenter)

        mainContent.addSpacerItem(QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        layout.addLayout(mainContent, 2, 0)

        # manual_button = QPushButton("Enter details manually")
        # manual_button.setFont(QFont("Kulim Park", 25))
        # manual_button.setStyleSheet("""
        #     QPushButton {
        #         background-color: white;
        #         color: black;
        #         border-radius: 20px;
        #         padding: 15px;
        #         margin: 20px;
        #     }
        #     QPushButton:hover {
        #         background-color: #dddddd;
        #     }
        # """)
        # manual_button.clicked.connect(self.showManualCardDetailsScreen)
        # layout.addWidget(manual_button)

        return widget

    def createManualCardDetailsScreen(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)

        # Top layout with logo
        topLayout = QHBoxLayout()
        topLayout.addStretch()
        text_logo = QLabel()
        pixmap = QPixmap(getImagePath('text_logo.png'))
        text_logo.setPixmap(pixmap)
        text_logo.setFixedHeight(50)
        topLayout.addWidget(text_logo)
        layout.addLayout(topLayout, 0, 0)

        # Divider line
        divider = QLabel()
        divider.setFixedHeight(3)
        divider.setStyleSheet("background-color: white;")
        layout.addWidget(divider)

        # Main content
        mainContent = QVBoxLayout()
        mainContent.setSpacing(20)

        title = QLabel("Payment")
        title.setFont(QFont("Kulim Park", 30))
        title.setStyleSheet(
            "color: white; font-weight: semibold; margin-top: 25px;")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        mainContent.addWidget(title)

        price_text = QLabel("10.50€")
        price_text.setFont(QFont("Kulim Park", 25))
        price_text.setStyleSheet(
            "color: white; font-weight: semibold; margin-left: 2px;")
        price_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
        mainContent.addWidget(price_text)

        # Card selection dropdown
        card_label = QLabel("Please select your card")
        card_label.setStyleSheet("color: white; font-size: 16px;")
        mainContent.addWidget(card_label)

        self.card_dropdown = QComboBox()
        self.card_dropdown.addItems(
            ["XX", "VS", "MC", "CA", "DC", "DN",
             "IN", "AX", "JC", "MA", "CU", "DS"])
        self.card_dropdown.setStyleSheet(
            "background-color: white; color: #181818;")
        mainContent.addWidget(self.card_dropdown)

        # Card number input
        self.card_number_input = QLineEdit()
        self.card_number_input.setPlaceholderText("Card Number")
        self.card_number_input.setStyleSheet(
            "background-color: white; padding: 5px; color: #181818;")
        mainContent.addWidget(self.card_number_input)

        # Expiration date and security code
        exp_layout = QHBoxLayout()

        self.exp_month = QLineEdit()
        self.exp_month.setPlaceholderText("MM")
        self.exp_month.setMaxLength(2)
        self.exp_month.setFixedWidth(50)
        self.exp_month.setStyleSheet(
            "background-color: white; padding: 5px; color: #181818;")
        exp_layout.addWidget(self.exp_month)

        self.exp_year = QLineEdit()
        self.exp_year.setPlaceholderText("YY")
        self.exp_year.setMaxLength(2)
        self.exp_year.setFixedWidth(50)
        self.exp_year.setStyleSheet(
            "background-color: white; padding: 5px; color: #181818;")
        exp_layout.addWidget(self.exp_year)

        # CVV
        self.cvv_input = QLineEdit()
        self.cvv_input.setPlaceholderText("CVV")
        self.cvv_input.setMaxLength(4)
        self.cvv_input.setFixedWidth(60)
        self.cvv_input.setStyleSheet(
            "background-color: white; padding: 5px; color: #181818;")

        exp_cvv_layout = QHBoxLayout()

        exp_cvv_layout.addLayout(exp_layout)
        exp_cvv_layout.addWidget(self.cvv_input)

        mainContent.addLayout(exp_cvv_layout)

        self.card_number_input.setInputMethodHints(
            Qt.InputMethodHint.ImhDigitsOnly)
        self.exp_month.setInputMethodHints(Qt.InputMethodHint.ImhDigitsOnly)
        self.exp_year.setInputMethodHints(Qt.InputMethodHint.ImhDigitsOnly)
        self.cvv_input.setInputMethodHints(Qt.InputMethodHint.ImhDigitsOnly)

        self.card_number_input.setMaxLength(19)  # 16 digits + 3 spaces
        self.exp_month.setMaxLength(2)           # MM
        self.exp_year.setMaxLength(2)            # YY
        self.cvv_input.setMaxLength(3)

        # Spacer before Pay button
        mainContent.addSpacerItem(QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Pay button
        pay_button = QPushButton("Pay")
        pay_button.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #181818;
                font-size: 18px;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """)
        pay_button.clicked.connect(self.showMessagesScreen)
        pay_button.clicked.connect(self.handleManualPayButtonClicked)

        mainContent.addWidget(
            pay_button, alignment=Qt.AlignmentFlag.AlignCenter)
        mainContent.addSpacerItem(QSpacerItem(
            20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        layout.addLayout(mainContent, 2, 0)

        return widget

    def createMessagesScreen(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)

        # Top layout with logo
        topLayout = QHBoxLayout()
        topLayout.addStretch()
        text_logo = QLabel()
        pixmap = QPixmap(getImagePath('text_logo.png'))
        text_logo.setPixmap(pixmap)
        text_logo.setFixedHeight(50)
        topLayout.addWidget(text_logo)
        layout.addLayout(topLayout, 0, 0)

        # Divider line
        divider = QLabel()
        divider.setFixedHeight(3)
        divider.setStyleSheet("background-color: white;")
        layout.addWidget(divider)

        # Main content
        mainContent = QVBoxLayout()
        mainContent.setSpacing(20)

        # Terminal Status Section
        terminal_status_title = QLabel("Terminal Status")
        terminal_status_title.setStyleSheet(
            "font-weight: bold; font-size: 14px;")
        mainContent.addWidget(terminal_status_title)

        terminal_status_layout = QHBoxLayout()
        # Status options mapping
        self.terminal_status_response_options = [
            ("Idle", TerminalStatusResponseCode.IDLE),
            ("Card inserted", TerminalStatusResponseCode.CARD_INSERTED),
            ("Card removed", TerminalStatusResponseCode.CARD_REMOVED),
            ("Chip card accepted", TerminalStatusResponseCode.CHIP_CARD_ACCEPTED),
            ("Swiped card accepted", TerminalStatusResponseCode.SWIPED_CARD_ACCEPTED),
            ("Contactless card accepted",
             TerminalStatusResponseCode.CONTACTLESS_CARD_ACCEPTED),
            ("Card identification", TerminalStatusResponseCode.CARD_IDENTIFICATION),
            ("Card not accepted", TerminalStatusResponseCode.CARD_NOT_ACCEPTED),
            ("Enter PIN", TerminalStatusResponseCode.ENTER_PIN),
            ("PIN accepted", TerminalStatusResponseCode.PIN_ACCEPTED),
            ("Wrong PIN", TerminalStatusResponseCode.WRONG_PIN),
            ("Authorization processing",
             TerminalStatusResponseCode.AUTHORIZATION_PROCESSING),
            ("Authorization approved",
             TerminalStatusResponseCode.AUTHORIZATION_APPROVED),
            ("Authorization declined",
             TerminalStatusResponseCode.AUTHORIZATION_DECLINED),
            ("Insert card", TerminalStatusResponseCode.INSERT_CARD),
            ("Void processing", TerminalStatusResponseCode.VOID_PROCESSING),
            ("Initialization processing",
             TerminalStatusResponseCode.INITIALIZATION_PROCESSING),
            ("Shift close processing",
             TerminalStatusResponseCode.SHIFT_CLOSE_PROCESSING),
            ("Activation processing", TerminalStatusResponseCode.ACTIVATION_PROCESSING),
            ("Deactivation processing",
             TerminalStatusResponseCode.DEACTIVATION_PROCESSING),
            ("Download processing", TerminalStatusResponseCode.DOWNLOAD_PROCESSING),
            ("Top-up processing", TerminalStatusResponseCode.TOP_UP_PROCESSING),
            ("Refund processing", TerminalStatusResponseCode.REFUND_PROCESSING),
            ("Terminal is error", TerminalStatusResponseCode.TERMINAL_IS_ERROR),
            ("Terminal is deactivated",
             TerminalStatusResponseCode.TERMINAL_IS_DEACTIVATED),
            ("Terminal is busy", TerminalStatusResponseCode.TERMINAL_IS_BUSY),
            ("Terminal not configured",
             TerminalStatusResponseCode.TERMINAL_NOT_CONFIGURED),
            ("Terminal unavailable", TerminalStatusResponseCode.TERMINAL_UNAVAILABLE),
            ("Fault request", TerminalStatusResponseCode.FAULT_REQUEST),
        ]

        # Dropdown menu
        self.terminal_status_dropdown = QComboBox()
        self.terminal_status_dropdown.addItems([option[0]
                                                for option in self.terminal_status_response_options])
        terminal_status_layout.addWidget(self.terminal_status_dropdown)

        # Execute button
        send_terminal_status_button = QPushButton("Send Terminal Status")
        send_terminal_status_button.clicked.connect(
            self.execute_selected_terminal_status)
        terminal_status_layout.addWidget(send_terminal_status_button)

        mainContent.addLayout(terminal_status_layout)

        # Display Message Section
        display_message_title = QLabel("Display Message")
        display_message_title.setStyleSheet(
            "font-weight: bold; font-size: 14px;")
        mainContent.addWidget(display_message_title)

        display_message_layout = QHBoxLayout()

        # Text input
        self.display_message_text_input = QLineEdit()
        self.display_message_text_input.setPlaceholderText("Enter message...")
        display_message_layout.addWidget(self.display_message_text_input)

        # Numeric input
        self.display_message_numeric_input = QSpinBox()
        self.display_message_numeric_input.setRange(0, 9999)
        self.display_message_numeric_input.setValue(0)
        display_message_layout.addWidget(self.display_message_numeric_input)

        # Display message level dropdown
        self.display_message_level_dropdown = QComboBox()
        self.display_message_level_options = [
            ("INFO", DisplayMessageLevel.INFO),
            ("ERROR", DisplayMessageLevel.ERROR),
        ]
        self.display_message_level_dropdown.addItems([option[0]
                                                      for option in self.display_message_level_options])
        display_message_layout.addWidget(self.display_message_level_dropdown)

        # Send display message button
        send_display_message_button = QPushButton("Send Display Message")
        send_display_message_button.clicked.connect(
            self.send_display_message_clicked)
        display_message_layout.addWidget(send_display_message_button)

        mainContent.addLayout(display_message_layout)

        # Transaction response section
        transaction_response_title = QLabel("Transaction Response")
        transaction_response_title.setStyleSheet(
            "font-weight: bold; font-size: 14px;")
        mainContent.addWidget(transaction_response_title)

        transaction_response_layout = QHBoxLayout()
        self.transaction_response_options = [
            ("Authorized", TransactionResponseCode.AUTHORISED),
            ("Referred", TransactionResponseCode.REFERRED),
            ("Referred Special Conditions",
             TransactionResponseCode.REFERRED_SPECIAL_CONDITIONS),
            ("Invalid Merchant", TransactionResponseCode.INVALID_MERCHANT),
            ("Hold Card", TransactionResponseCode.HOLD_CARD),
            ("Refused", TransactionResponseCode.REFUSED),
            ("Error", TransactionResponseCode.ERROR),
            ("Hold Card Special Conditions",
             TransactionResponseCode.HOLD_CARD_SPECIAL_CONDITIONS),
            ("Approve After Identification",
             TransactionResponseCode.APPROVE_AFTER_IDENTIFICATION),
            ("Approved for Partial Amount",
             TransactionResponseCode.APPROVED_FOR_PARTIAL_AMOUNT),
            ("Approved VIP", TransactionResponseCode.APPROVED_VIP),
            ("Invalid Transaction", TransactionResponseCode.INVALID_TRANSACTION),
            ("Invalid Amount", TransactionResponseCode.INVALID_AMOUNT),
            ("Invalid Account", TransactionResponseCode.INVALID_ACCOUNT),
            ("Invalid Card Issuer", TransactionResponseCode.INVALID_CARD_ISSUER),
            ("Approved Update Track3", TransactionResponseCode.APPROVED_UPDATE_TRACK3),
            ("Annulation by Client", TransactionResponseCode.ANNULATION_BY_CLIENT),
            ("Customer Dispute", TransactionResponseCode.CUSTOMER_DISPUTE),
            ("Re-enter Transaction", TransactionResponseCode.RE_ENTER_TRANSACTION),
            ("Invalid Response", TransactionResponseCode.INVALID_RESPONSE),
            ("No Action Taken", TransactionResponseCode.NO_ACTION_TAKEN),
            ("Suspected Malfunction", TransactionResponseCode.SUSPECTED_MALFUNCTION),
            ("Unacceptable Transaction Fee",
             TransactionResponseCode.UNACCEPTABLE_TRANSACTION_FEE,),
            ("Access Denied", TransactionResponseCode.ACCESS_DENIED),
            ("Format Error", TransactionResponseCode.FORMAT_ERROR),
            ("Unknown Acquirer Account",
             TransactionResponseCode.UNKNOWN_ACQUIRER_ACCOUNT),
            ("Card Expired", TransactionResponseCode.CARD_EXPIRED),
            ("Fraud Suspicion", TransactionResponseCode.FRAUD_SUSPICION),
            ("Security Code Expired", TransactionResponseCode.SECURITY_CODE_EXPIRED),
            ("Function Not Supported", TransactionResponseCode.FUNCTION_NOT_SUPPORTED),
            ("Lost Card", TransactionResponseCode.LOST_CARD),
            ("Stolen Card", TransactionResponseCode.STOLEN_CARD),
            ("Limit Exceeded", TransactionResponseCode.LIMIT_EXCEEDED),
            ("Card Expired Pick Up", TransactionResponseCode.CARD_EXPIRED_PICK_UP),
            ("Invalid Security Code", TransactionResponseCode.INVALID_SECURITY_CODE),
            ("Unknown Card", TransactionResponseCode.UNKNOWN_CARD),
            ("Illegal Transaction", TransactionResponseCode.ILLEGAL_TRANSACTION),
            ("Transaction Not Permitted",
             TransactionResponseCode.TRANSACTION_NOT_PERMITTED),
            ("Restricted Card", TransactionResponseCode.RESTRICTED_CARD),
            ("Security Rules Violated",
             TransactionResponseCode.SECURITY_RULES_VIOLATED),
            ("Exceed Withdrawal Frequency",
             TransactionResponseCode.EXCEED_WITHDRAWAL_FREQUENCY),
            ("Transaction Timed Out", TransactionResponseCode.TRANSACTION_TIMED_OUT),
            ("Exceed PIN Tries", TransactionResponseCode.EXCEED_PIN_TRIES),
            ("Invalid Debit Account", TransactionResponseCode.INVALID_DEBIT_ACCOUNT),
            ("Invalid Credit Account", TransactionResponseCode.INVALID_CREDIT_ACCOUNT),
            ("Blocked First Used", TransactionResponseCode.BLOCKED_FIRST_USED),
            ("Credit Issuer Unavailable",
             TransactionResponseCode.CREDIT_ISSUER_UNAVAILABLE),
            ("PIN Cryptographic Error",
             TransactionResponseCode.PIN_CRYPROGRAPHIC_ERROR),
            ("Incorrect CCV", TransactionResponseCode.INCORRECT_CCV),
            ("Unable to Verify PIN", TransactionResponseCode.UNABLE_TO_VERIFY_PIN),
            ("Rejected by Card Issuer",
             TransactionResponseCode.REJECTED_BY_CARD_ISSUER),
            ("Issuer Unavailable", TransactionResponseCode.ISSUER_UNAVAILABLE),
            ("Routing Error", TransactionResponseCode.ROUTING_ERROR),
            ("Transaction Cannot Complete",
             TransactionResponseCode.TRANSACTION_CANNOT_COMPLETE),
            ("Duplicate Transaction", TransactionResponseCode.DUPLICATE_TRANSACTION),
            ("System Error", TransactionResponseCode.SYSTEM_ERROR),
            ("Offline Authorised", TransactionResponseCode.OFFLINE_AUTHORISED),
            ("Issuer Unavailable Authorised",
             TransactionResponseCode.ISSUER_UNAVAILABLE_AUTHORISED,),
            ("Offline Refused", TransactionResponseCode.OFFLINE_REFUSED),
            ("Issuer Unavailable Refused",
             TransactionResponseCode.ISSUER_UNAVAILABLE_REFUSED,),
            ("Transaction Canceled by Merchant",
             TransactionResponseCode.Transaction_canceled_by_Merchant),
            ("Transaction Canceled by Terminal User",
             TransactionResponseCode.Transaction_canceled_by_terminal_user,),
            ("Transaction Canceled After Exception",
             TransactionResponseCode.Transaction_canceled_after_exception,),
            ("Transaction Canceled After Removed Card",
             TransactionResponseCode.Transaction_canceled_after_removed_card,),
            ("Terminal is Deactivated",
             TransactionResponseCode.Terminal_is_deactivated),
            ("Terminal is Busy", TransactionResponseCode.Terminal_is_busy),
            ("Terminal Not Configured",
             TransactionResponseCode.Terminal_not_configured),
            ("Terminal Unavailable", TransactionResponseCode.Terminal_unavailable),
            ("Fault Request", TransactionResponseCode.Fault_request),
        ]

        # Dropdown menu
        self.transaction_response_dropdown = QComboBox()
        self.transaction_response_dropdown.addItems([option[0]
                                                     for option in self.transaction_response_options])
        transaction_response_layout.addWidget(
            self.transaction_response_dropdown)

        # Execute button
        send_transaction_response_button = QPushButton("Send Terminal Status")
        send_transaction_response_button.clicked.connect(
            self.execute_selected_transaction_response)
        transaction_response_layout.addWidget(send_transaction_response_button)

        mainContent.addLayout(transaction_response_layout)

        layout.addLayout(mainContent, 2, 0)
        return widget

    def send_display_message_clicked(self):
        message = self.display_message_text_input.text()
        numeric_value = self.display_message_numeric_input.value()
        level_index = self.display_message_level_dropdown.currentIndex()
        level = self.display_message_level_options[level_index][1]

        self.send_display_message.emit(message, numeric_value, level)

    def execute_selected_terminal_status(self):
        selected_index = self.terminal_status_dropdown.currentIndex()
        selected_option = self.terminal_status_response_options[selected_index]

        self.send_status_signal.emit(selected_option[1])

    def execute_selected_transaction_response(self):
        selected_index = self.transaction_response_dropdown.currentIndex()
        selected_option = self.transaction_response_options[selected_index]

        global card_details
        self.send_transaction_response.emit(selected_option[1], card_details)

    def handleSimulatedPayButtonClicked(self):
        self.send_status_signal.emit(
            TerminalStatusResponseCode.INSERT_CARD)

        time.sleep(0.5)

        self.send_display_message.emit(
            "4,00 Insert card",
            1,
            DisplayMessageLevel.INFO)

        time.sleep(0.5)

        self.send_status_signal.emit(
            TerminalStatusResponseCode.CARD_INSERTED)

        time.sleep(0.5)

        self.send_display_message.emit(
            "Please wait",
            2,
            DisplayMessageLevel.INFO)

        time.sleep(0.5)

        self.send_status_signal.emit(
            TerminalStatusResponseCode.CARD_IDENTIFICATION)

        time.sleep(0.5)

        self.send_status_signal.emit(
            TerminalStatusResponseCode.CHIP_CARD_ACCEPTED)

        time.sleep(0.5)

        self.send_display_message.emit(
            "Credit Card Amex",
            3,
            DisplayMessageLevel.INFO)

        time.sleep(0.5)

        self.send_status_signal.emit(
            TerminalStatusResponseCode.ENTER_PIN)

        time.sleep(0.5)

        self.send_display_message.emit(
            "4,00 $ Enter PIN",
            10,
            DisplayMessageLevel.INFO)

        time.sleep(0.5)

        self.send_display_message.emit(
            "*   ",
            11,
            DisplayMessageLevel.INFO)

        time.sleep(0.5)

        self.send_display_message.emit(
            "**  ",
            12,
            DisplayMessageLevel.INFO)

        time.sleep(0.5)

        self.send_display_message.emit(
            "*** ",
            13,
            DisplayMessageLevel.INFO)

        time.sleep(0.5)

        self.send_display_message.emit(
            "****",
            14,
            DisplayMessageLevel.INFO)

        time.sleep(0.5)

        self.send_status_signal.emit(
            TerminalStatusResponseCode.PIN_ACCEPTED)

        time.sleep(0.5)

        self.send_status_signal.emit(
            TerminalStatusResponseCode.AUTHORIZATION_PROCESSING)

        time.sleep(0.5)

        self.send_display_message.emit(
            "Please wait",
            1,
            DisplayMessageLevel.INFO)

        time.sleep(0.5)

        self.send_status_signal.emit(
            TerminalStatusResponseCode.AUTHORIZATION_APPROVED)

        time.sleep(0.5)

        self.send_display_message.emit(
            "Accepted Take card",
            100,
            DisplayMessageLevel.INFO)

        time.sleep(0.5)

        self.send_status_signal.emit(
            TerminalStatusResponseCode.CARD_REMOVED)

        time.sleep(0.5)

        self.handlePayButtonClicked()
        self.pay_button_clicked.emit(card_details)

    def handleQuickPayButtonClicked(self):

        self.send_status_signal.emit(
            TerminalStatusResponseCode.CARD_INSERTED)

        time.sleep(0.2)

        self.handlePayButtonClicked()
        self.pay_button_clicked.emit(card_details)

    def handlePayButtonClicked(self):
        global config, card_details
        card_details = {
            "card_number": config.card_number,
            "expiration_date": config.expiration_date,
            "cvv": config.cvv,
            "card_issuer": config.card_issuer
        }
        print(f"INFO: Saved card details:\n {card_details}")

    def handleManualPayButtonClicked(self):
        global card_details
        card_details = {
            "card_number": self.card_number_input.text(),
            "expiration_date": self.exp_month.text() + self.exp_year.text(),
            "cvv": self.cvv_input.text(),
            "card_issuer": self.card_dropdown.currentText()
        }
        print(f"INFO: Saved card details:\n {card_details}")

    def saveSettings(self):
        global config

        port = int(self.port_input.text()
                   ) if self.port_input.text().isdigit() else 0
        send_response = self.send_response_toggle.isChecked()
        card_number = self.card_number_input_settings.text()
        month = self.exp_month_settings.text()
        year = self.exp_year_settings.text()
        expiration = f"{month}{year}"

        config.port = port
        config.send_rsp_before_timeout = send_response
        config.card_number = card_number
        config.expiration_date = expiration

        save_config(config)

        print("INFO: Settings saved")

    def showSettingsScreen(self):
        """Switches to the settings screen."""
        if self.server_thread and self.server_thread.isRunning():
            self.server_thread.stop()
            try:
                self.server_thread.connection_handler.price_updated.disconnect(
                    self.showPaymentScreen)
                self.server_thread.connection_handler.client_disconnected.disconnect(
                    self.showIdleScreen)
                self.pay_button_clicked.disconnect(
                    self.server_thread.connection_handler.send_payment)
                self.send_status_signal.disconnect(
                    self.server_thread.connection_handler.recieve_status_from_ui)
                self.send_display_message.disconnect(
                    self.server_thread.connection_handler.recieve_display_from_ui)
                self.send_transaction_response.disconnect(
                    self.server_thread.connection_handler.recieve_transaction_response_from_ui)
            except TypeError:
                pass
            self.server_thread = None

        self.setCentralWidget(self.createSettingsScreen())

    def showIdleScreen(self):
        """Switches to the main idle screen."""
        global config

        if not self.server_thread:
            self.server_thread = ServerThread(
                config.port, self)
            self.server_thread.connection_handler.price_updated.connect(
                self.showPaymentScreen)
            self.server_thread.connection_handler.client_disconnected.connect(
                self.showIdleScreen)
            self.pay_button_clicked.connect(
                self.server_thread.connection_handler.send_payment)
            self.send_status_signal.connect(
                self.server_thread.connection_handler.recieve_status_from_ui)
            self.send_display_message.connect(
                self.server_thread.connection_handler.recieve_display_from_ui)
            self.send_transaction_response.connect(
                self.server_thread.connection_handler.recieve_transaction_response_from_ui)
            self.server_thread.start()

        self.setCentralWidget(self.createIdleScreen())

    def showPaymentScreen(self, price: str):
        """Switches to the payment screen."""
        self.setCentralWidget(self.createPaymentScreen(price))

    def showManualCardDetailsScreen(self):
        """Switches to the manual card details screen."""
        self.setCentralWidget(self.createManualCardDetailsScreen())

    def showMessagesScreen(self):
        """Switches to the messages screen."""
        if self.server_thread is None:
            print("ERROR: No server thread")
            return

        self.setCentralWidget(self.createMessagesScreen())

    def closeEvent(self, event):
        """Ensures the server thread is stopped when the window is closed."""
        if self.server_thread and self.server_thread.isRunning():
            self.server_thread.stop()
            try:
                self.server_thread.connection_handler.price_updated.disconnect(
                    self.showPaymentScreen)
                self.server_thread.connection_handler.client_disconnected.disconnect(
                    self.showIdleScreen)
                self.pay_button_clicked.disconnect(
                    self.server_thread.connection_handler.send_payment)
                self.send_status_signal.disconnect(
                    self.server_thread.connection_handler.recieve_status_from_ui)
                self.send_display_message.disconnect(
                    self.server_thread.connection_handler.recieve_display_from_ui)
                self.send_transaction_response.disconnect(
                    self.server_thread.connection_handler.recieve_transaction_response_from_ui)
            except TypeError:
                pass
        event.accept()
