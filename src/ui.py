import os
import functools
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
    QTimer,
    QPointF,
    Signal,
    Slot,
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

STYLESHEET = """
#MainWindow {
    background-color: #181818;
}

QWidget {
    color: #F0F0F0;
    font-family: "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif;
}
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #333333;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #007ACC;
}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
    background-color: #2A2A2A;
    color: #777777;
}

QPushButton {
    background-color: #007ACC;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #0099FF;
}
QPushButton:pressed {
    background-color: #005FAA;
}
QPushButton:disabled {
    background-color: #2A2A2A;
    color: #777777;
}

QComboBox {
    background-color: #333333;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px;
}
QComboBox:hover {
    border: 1px solid #777777;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #555555;
}
QComboBox QAbstractItemView {
    background-color: #222222;
    border: 1px solid #555555;
    selection-background-color: #007ACC;
    selection-color: #FFFFFF;
    outline: 0px;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #555555;
    border-radius: 9px;
    background-color: #333333;
}
QRadioButton::indicator:hover {
    border: 1px solid #777777;
}
QRadioButton::indicator:checked {
    background-color: #007ACC;
    border: 1px solid #007ACC;
}
QRadioButton:disabled {
    color: #777777;
}
QRadioButton::indicator:disabled {
    background-color: #2A2A2A;
    border: 1px solid #444444;
}
"""


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
        painter.setFont(QFont("Kulim Park", 20))
        painter.drawText(
            self.rect(), Qt.AlignmentFlag.AlignCenter, self.text)


class MainWindow(QMainWindow):
    pay_button_clicked = Signal(dict)
    send_status_signal = Signal(TerminalStatusResponseCode)
    send_display_signal = Signal(str, int, DisplayMessageLevel)
    send_transaction_signal = Signal(TransactionResponseCode, dict)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("SBTerminal")
        self.setObjectName("MainWindow")
        self.setFixedSize(QSize(480, 800))
        self.setStyleSheet(STYLESHEET)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.card_details: dict
        self.price_text_value: str
        self.sent_message: str = ""

        self.server_thread: ServerThread | None = None

        self.send_status_signal_message_handler = lambda code: self.update_sent_message(
            code._name_.replace("_", " "))
        self.send_display_signal_message_handler = lambda msg, _, __: self.update_sent_message(
            msg)
        self.send_transaction_signal_message_handler = lambda code, _: self.update_sent_message(
            code._name_.replace("_", " "))
        # Set the initial screen
        self.showIdleScreen()

    def createIdleScreen(self):
        """Creates and returns the main idle screen."""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
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
        layout.setContentsMargins(20, 20, 20, 20)
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

        x = QHBoxLayout()
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

        cvv_layout = QHBoxLayout()
        self.cvv_input_settings = QLineEdit(config.cvv)
        self.cvv_input_settings.setPlaceholderText("CVV")
        self.cvv_input_settings.setFixedWidth(60)
        cvv_layout.addWidget(self.cvv_input_settings)

        x.addLayout(exp_layout)
        x.addLayout(cvv_layout)
        card_layout.addLayout(x)
        card_group.setLayout(card_layout)
        layout.addWidget(card_group)

        network_group = QGroupBox("Network Settings")

        network_group.setStyleSheet("QGroupBox { color: white; }")
        network_layout = QHBoxLayout()
        self.ip_addres_input = QLineEdit(self.ip)
        self.ip_addres_input.setEnabled(False)
        self.ip_addres_input.setStyleSheet("color: #aaaaaa")
        self.port_input = QLineEdit(str(config.port))
        self.port_input.setValidator(QIntValidator(1, 65535))
        network_layout.addWidget(self.ip_addres_input)
        network_layout.addWidget(self.port_input)
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)

        # Toggle
        self.send_response_toggle = QCheckBox("Send Response")
        self.send_response_toggle.setChecked(config.send_rsp_before_timeout)
        layout.addWidget(self.send_response_toggle)

        layout.addStretch()

        return widget

    def createPaymentScreen(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
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

        price_text = QLabel(self.price_text_value)
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
        manual_pay_button.clicked.connect(self.showManualPaymentScreen)
        manual_pay_button.clicked.connect(self.load_card_details)

        quick_pay_button = DiamondButton("Quick\npay")
        quick_pay_button.setFixedSize(200, 200)
        quick_pay_button.setStyleSheet(
            "background-color: transparent; border: none;")
        quick_pay_button.clicked.connect(
            self.showSimplePaymentScreen)
        quick_pay_button.clicked.connect(self.load_card_details)
        quick_pay_button.clicked.connect(self.handleQuickPayButtonClicked)

        example_pay_button = DiamondButton("Example\nPay")
        example_pay_button.setFixedSize(200, 200)
        example_pay_button.setStyleSheet(
            "background-color: transparent; border: none;")
        example_pay_button.clicked.connect(
            self.showSimplePaymentScreen)
        example_pay_button.clicked.connect(self.load_card_details)
        example_pay_button.clicked.connect(
            self.handleSimulatedPayButtonClicked)

        button_layout.addWidget(
            manual_pay_button, alignment=Qt.AlignmentFlag.AlignCenter)

        button_layout.addWidget(
            example_pay_button, alignment=Qt.AlignmentFlag.AlignCenter)

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

    # def createManualCardDetailsScreen(self):
    #     widget = QWidget()
    #     layout = QGridLayout(widget)
    #     layout.setContentsMargins(20, 20, 20, 20)
    #     layout.setSpacing(0)
    #
    #     # Top layout with logo
    #     topLayout = QHBoxLayout()
    #     topLayout.addStretch()
    #     text_logo = QLabel()
    #     pixmap = QPixmap(getImagePath('text_logo.png'))
    #     text_logo.setPixmap(pixmap)
    #     text_logo.setFixedHeight(50)
    #     topLayout.addWidget(text_logo)
    #     layout.addLayout(topLayout, 0, 0)
    #
    #     # Divider line
    #     divider = QLabel()
    #     divider.setFixedHeight(3)
    #     divider.setStyleSheet("background-color: white;")
    #     layout.addWidget(divider)
    #
    #     # Main content
    #     mainContent = QVBoxLayout()
    #     mainContent.setSpacing(20)
    #
    #     title = QLabel("Payment")
    #     title.setFont(QFont("Kulim Park", 30))
    #     title.setStyleSheet(
    #         "color: white; font-weight: semibold; margin-top: 25px;")
    #     title.setAlignment(Qt.AlignmentFlag.AlignLeft)
    #     mainContent.addWidget(title)
    #
    #     price_text = QLabel("10.50€")
    #     price_text.setFont(QFont("Kulim Park", 25))
    #     price_text.setStyleSheet(
    #         "color: white; font-weight: semibold; margin-left: 2px;")
    #     price_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
    #     mainContent.addWidget(price_text)
    #
    #     # Card selection dropdown
    #     card_label = QLabel("Please select your card")
    #     card_label.setStyleSheet("color: white; font-size: 16px;")
    #     mainContent.addWidget(card_label)
    #
    #     self.card_dropdown = QComboBox()
    #     self.card_dropdown.addItems(
    #         ["XX", "VS", "MC", "CA", "DC", "DN",
    #          "IN", "AX", "JC", "MA", "CU", "DS"])
    #     self.card_dropdown.setStyleSheet(
    #         "background-color: white; color: #181818;")
    #     mainContent.addWidget(self.card_dropdown)
    #
    #     # Card number input
    #     self.card_number_input = QLineEdit()
    #     self.card_number_input.setPlaceholderText("Card Number")
    #     self.card_number_input.setStyleSheet(
    #         "background-color: white; padding: 5px; color: #181818;")
    #     mainContent.addWidget(self.card_number_input)
    #
    #     # Expiration date and security code
    #     exp_layout = QHBoxLayout()
    #
    #     self.exp_month = QLineEdit()
    #     self.exp_month.setPlaceholderText("MM")
    #     self.exp_month.setMaxLength(2)
    #     self.exp_month.setFixedWidth(50)
    #     self.exp_month.setStyleSheet(
    #         "background-color: white; padding: 5px; color: #181818;")
    #     exp_layout.addWidget(self.exp_month)
    #
    #     self.exp_year = QLineEdit()
    #     self.exp_year.setPlaceholderText("YY")
    #     self.exp_year.setMaxLength(2)
    #     self.exp_year.setFixedWidth(50)
    #     self.exp_year.setStyleSheet(
    #         "background-color: white; padding: 5px; color: #181818;")
    #     exp_layout.addWidget(self.exp_year)
    #
    #     # CVV
    #     self.cvv_input = QLineEdit()
    #     self.cvv_input.setPlaceholderText("CVV")
    #     self.cvv_input.setMaxLength(4)
    #     self.cvv_input.setFixedWidth(60)
    #     self.cvv_input.setStyleSheet(
    #         "background-color: white; padding: 5px; color: #181818;")
    #
    #     exp_cvv_layout = QHBoxLayout()
    #
    #     exp_cvv_layout.addLayout(exp_layout)
    #     exp_cvv_layout.addWidget(self.cvv_input)
    #
    #     mainContent.addLayout(exp_cvv_layout)
    #
    #     self.card_number_input.setInputMethodHints(
    #         Qt.InputMethodHint.ImhDigitsOnly)
    #     self.exp_month.setInputMethodHints(Qt.InputMethodHint.ImhDigitsOnly)
    #     self.exp_year.setInputMethodHints(Qt.InputMethodHint.ImhDigitsOnly)
    #     self.cvv_input.setInputMethodHints(Qt.InputMethodHint.ImhDigitsOnly)
    #
    #     self.card_number_input.setMaxLength(19)  # 16 digits + 3 spaces
    #     self.exp_month.setMaxLength(2)           # MM
    #     self.exp_year.setMaxLength(2)            # YY
    #     self.cvv_input.setMaxLength(3)
    #
    #     # Spacer before Pay button
    #     mainContent.addSpacerItem(QSpacerItem(
    #         20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
    #
    #     # Pay button
    #     pay_button = QPushButton("Pay")
    #     pay_button.setStyleSheet("""
    #         QPushButton {
    #             background-color: #ffffff;
    #             color: #181818;
    #             font-size: 18px;
    #             padding: 10px 20px;
    #             border-radius: 5px;
    #         }
    #         QPushButton:hover {
    #             background-color: #dddddd;
    #         }
    #     """)
    #     pay_button.clicked.connect(self.showManualPaymentScreen)
    #     pay_button.clicked.connect(self.handleManualPayButtonClicked)
    #
    #     mainContent.addWidget(
    #         pay_button, alignment=Qt.AlignmentFlag.AlignCenter)
    #     mainContent.addSpacerItem(QSpacerItem(
    #         20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
    #
    #     layout.addLayout(mainContent, 2, 0)
    #
    #     return widget

    def createSimplePaymentScreen(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
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

        title = QLabel("Example Pay")
        title.setFont(QFont("Kulim Park", 50))
        title.setStyleSheet(
            "color: white; font-weight: semibold; margin-top: 50px;")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        mainContent.addWidget(title)

        price_text = QLabel(self.price_text_value)
        price_text.setFont(QFont("Kulim Park", 30))
        price_text.setStyleSheet(
            "color: white; font-weight: semibold; margin-left: 10px;")
        price_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
        mainContent.addWidget(price_text)

        self.sent_message_text = QLabel(self.sent_message)
        self.sent_message_text.setWordWrap(True)
        self.sent_message_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.sent_message_text.setFont(QFont("Kulim Park", 30))
        self.sent_message_text.setStyleSheet(
            "color: white; font-weight: semibold; margin-left: 10px;")
        mainContent.addWidget(self.sent_message_text)

        mainContent.addSpacerItem(QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        layout.addLayout(mainContent, 2, 0)
        return widget

    def createManualPaymentScreen(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
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

        title = QLabel("Manual Pay")
        title.setFont(QFont("Kulim Park", 50))
        title.setStyleSheet(
            "color: white; font-weight: semibold; margin-top: 50px;")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        mainContent.addWidget(title)

        price_text = QLabel(self.price_text_value)
        price_text.setFont(QFont("Kulim Park", 30))
        price_text.setStyleSheet(
            "color: white; font-weight: semibold; margin-left: 10px;")
        price_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
        mainContent.addWidget(price_text)

        self.sent_message_text = QLabel(self.sent_message)
        self.sent_message_text.setWordWrap(True)
        self.sent_message_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.sent_message_text.setFont(QFont("Kulim Park", 30))
        self.sent_message_text.setStyleSheet(
            "color: white; font-weight: semibold; margin-left: 10px;")
        mainContent.addWidget(self.sent_message_text)

        mainContent.addSpacerItem(QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Terminal Status Section
        terminal_status_group = QGroupBox("Terminal Status")
        terminal_status_group.setStyleSheet(
            """
                QGroupBox { font-weight: bold; font-size: 14px;}
            """
        )

        terminal_status_layout = QHBoxLayout(terminal_status_group)
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

        mainContent.addWidget(terminal_status_group)

        # Display Message Section
        display_message_group = QGroupBox("Display Message")
        display_message_group.setStyleSheet(
            """
                QGroupBox { font-weight: bold; font-size: 14px;}
            """
        )

        display_message_layout = QVBoxLayout(display_message_group)

        # Text input
        self.display_message_text_input = QLineEdit()
        self.display_message_text_input.setPlaceholderText("Enter message...")
        display_message_layout.addWidget(self.display_message_text_input)

        stuff = QHBoxLayout()

        # Numeric input
        self.display_message_numeric_input = QSpinBox()
        self.display_message_numeric_input.setRange(0, 9999)
        self.display_message_numeric_input.setValue(0)
        stuff.addWidget(self.display_message_numeric_input)

        # Display message level dropdown
        self.display_message_level_dropdown = QComboBox()
        self.display_message_level_options = [
            ("INFO", DisplayMessageLevel.INFO),
            ("ERROR", DisplayMessageLevel.ERROR),
        ]
        self.display_message_level_dropdown.addItems([option[0]
                                                      for option in self.display_message_level_options])
        stuff.addWidget(self.display_message_level_dropdown)

        # Send display message button
        send_display_message_button = QPushButton("Send Display Message")
        send_display_message_button.clicked.connect(
            self.send_display_message_clicked)
        stuff.addWidget(send_display_message_button)

        display_message_layout.addLayout(stuff)

        mainContent.addWidget(display_message_group)

        # Transaction response section
        transaction_response_group = QGroupBox("Transaction Response")
        transaction_response_group.setStyleSheet(
            """
                QGroupBox { font-weight: bold; font-size: 14px;}
            """
        )
        transaction_response_layout = QHBoxLayout(transaction_response_group)

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

        mainContent.addWidget(transaction_response_group)

        layout.addLayout(mainContent, 2, 0)
        return widget

    def send_display_message_clicked(self):
        message = self.display_message_text_input.text()
        numeric_value = self.display_message_numeric_input.value()
        level_index = self.display_message_level_dropdown.currentIndex()
        level = self.display_message_level_options[level_index][1]

        self.send_display_signal.emit(message, numeric_value, level)

    def execute_selected_terminal_status(self):
        selected_index = self.terminal_status_dropdown.currentIndex()
        selected_option = self.terminal_status_response_options[selected_index]

        self.send_status_signal.emit(selected_option[1])

    def execute_selected_transaction_response(self):
        selected_index = self.transaction_response_dropdown.currentIndex()
        selected_option = self.transaction_response_options[selected_index]

        self.send_transaction_signal.emit(
            selected_option[1], self.card_details)

    def update_sent_message(self, message: str):
        self.sent_message = message
        self.sent_message_text.setText(self.sent_message)

    def handleSimulatedPayButtonClicked(self, step: int = 0):
        if step == 0:
            self.send_status_signal.emit(
                TerminalStatusResponseCode.INSERT_CARD)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=1))
        elif step == 1:
            self.send_display_signal.emit(
                "4,00 Insert card",
                1,
                DisplayMessageLevel.INFO)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=2))
        elif step == 2:
            self.send_status_signal.emit(
                TerminalStatusResponseCode.CARD_INSERTED)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=3))
        elif step == 3:
            self.send_display_signal.emit(
                "Please wait",
                2,
                DisplayMessageLevel.INFO)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=4))
        elif step == 4:
            self.send_status_signal.emit(
                TerminalStatusResponseCode.CARD_IDENTIFICATION)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=5))
        elif step == 5:
            self.send_status_signal.emit(
                TerminalStatusResponseCode.CHIP_CARD_ACCEPTED)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=6))
        elif step == 6:
            self.send_display_signal.emit(
                "Credit Card Amex",
                3,
                DisplayMessageLevel.INFO)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=7))
        elif step == 7:
            self.send_status_signal.emit(
                TerminalStatusResponseCode.ENTER_PIN)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=8))
        elif step == 8:
            self.send_display_signal.emit(
                "4,00 $ Enter PIN",
                10,
                DisplayMessageLevel.INFO)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=9))
        elif step == 9:
            self.send_display_signal.emit(
                "*   ",
                11,
                DisplayMessageLevel.INFO)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=10))
        elif step == 10:
            self.send_display_signal.emit(
                "**  ",
                12,
                DisplayMessageLevel.INFO)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=11))
        elif step == 11:
            self.send_display_signal.emit(
                "*** ",
                13,
                DisplayMessageLevel.INFO)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=12))
        elif step == 12:
            self.send_display_signal.emit(
                "****",
                14,
                DisplayMessageLevel.INFO)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=13))
        elif step == 13:
            self.send_status_signal.emit(
                TerminalStatusResponseCode.PIN_ACCEPTED)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=14))
        elif step == 14:
            self.send_status_signal.emit(
                TerminalStatusResponseCode.AUTHORIZATION_PROCESSING)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=15))
        elif step == 15:
            self.send_display_signal.emit(
                "Please wait",
                1,
                DisplayMessageLevel.INFO)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=16))
        elif step == 16:
            self.send_status_signal.emit(
                TerminalStatusResponseCode.AUTHORIZATION_APPROVED)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=17))
        elif step == 17:
            self.send_display_signal.emit(
                "Accepted Take card",
                100,
                DisplayMessageLevel.INFO)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=18))
        elif step == 18:
            self.send_status_signal.emit(
                TerminalStatusResponseCode.CARD_REMOVED)
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=19))
        elif step == 19:
            self.send_transaction_signal.emit(
                TransactionResponseCode.AUTHORISED,
                self.card_details
            )
            QTimer.singleShot(500, functools.partial(
                self.handleSimulatedPayButtonClicked, step=20))

    def handleQuickPayButtonClicked(self, step: int = 0):
        if step == 0:
            self.send_status_signal.emit(
                TerminalStatusResponseCode.CARD_INSERTED)
            QTimer.singleShot(500, functools.partial(
                self.handleQuickPayButtonClicked, step=1))
        elif step == 1:
            self.send_transaction_signal.emit(
                TransactionResponseCode.AUTHORISED,
                self.card_details
            )
            QTimer.singleShot(500, functools.partial(
                self.handleQuickPayButtonClicked, step=2))

    def load_card_details(self):
        global config
        self.card_details = {
            "card_number": config.card_number,
            "expiration_date": config.expiration_date,
            "cvv": config.cvv,
            "card_issuer": config.card_issuer
        }
        print(f"INFO: Saved card details:\n {self.card_details}")

    # def handleManualPayButtonClicked(self):
    #     self.card_details = {
    #         "card_number": self.card_number_input.text(),
    #         "expiration_date": self.exp_month.text() + self.exp_year.text(),
    #         "cvv": self.cvv_input.text(),
    #         "card_issuer": self.card_dropdown.currentText()
    #     }
    #     print(f"INFO: Saved card details:\n {self.card_details}")

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
                self.send_display_signal.disconnect(
                    self.server_thread.connection_handler.recieve_display_from_ui)
                self.send_transaction_signal.disconnect(
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
            self.send_display_signal.connect(
                self.server_thread.connection_handler.recieve_display_from_ui)
            self.send_transaction_signal.connect(
                self.server_thread.connection_handler.recieve_transaction_response_from_ui)
            self.send_status_signal.connect(
                self.send_status_signal_message_handler)
            self.send_display_signal.connect(
                self.send_display_signal_message_handler)
            self.send_transaction_signal.connect(
                self.send_transaction_signal_message_handler)

            self.server_thread.start()

            self.ip = self.server_thread.get_ip()

        self.setCentralWidget(self.createIdleScreen())

    def showPaymentScreen(self, price: str):
        """Switches to the payment screen."""
        self.price_text_value = price
        self.setCentralWidget(self.createPaymentScreen())

    # def showManualCardDetailsScreen(self):
    #     """Switches to the manual card details screen."""
    #     self.setCentralWidget(self.createManualCardDetailsScreen())

    def showSimplePaymentScreen(self):
        """Switches to the payment screen."""
        if self.server_thread is None:
            print("ERROR: No server thread")
            return

        self.setCentralWidget(self.createSimplePaymentScreen())

    def showManualPaymentScreen(self):
        """Switches to the messages screen."""
        if self.server_thread is None:
            print("ERROR: No server thread")
            return

        self.setCentralWidget(self.createManualPaymentScreen())

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
                self.send_display_signal.disconnect(
                    self.server_thread.connection_handler.recieve_display_from_ui)
                self.send_transaction_signal.disconnect(
                    self.server_thread.connection_handler.recieve_transaction_response_from_ui)
                self.send_status_signal.disconnect(
                    self.send_status_signal_message_handler)
                self.send_display_signal.disconnect(
                    self.send_display_signal_message_handler)
                self.send_transaction_signal.disconnect(
                    self.send_transaction_signal_message_handler)
            except TypeError:
                pass
        event.accept()
