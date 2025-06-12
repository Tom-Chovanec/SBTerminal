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

from message_generator import TerminalStatusResponseCode, DisplayMessageLevel
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

        insert_card_button = QPushButton("Insert Card")
        insert_card_button.setStyleSheet("""
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
        mainContent.addWidget(insert_card_button)

        card_inserted_button = QPushButton("Card Inserted")
        card_inserted_button.setStyleSheet("""
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
        mainContent.addWidget(card_inserted_button)

        card_identification_button = QPushButton("Card Identification")
        card_identification_button.setStyleSheet("""
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
        mainContent.addWidget(card_identification_button)

        chip_card_accepted_button = QPushButton("Chip card accepted")
        chip_card_accepted_button.setStyleSheet("""
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
        mainContent.addWidget(chip_card_accepted_button)

        enter_pin_button = QPushButton("Enter PIN")
        enter_pin_button.setStyleSheet("""
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
        mainContent.addWidget(enter_pin_button)

        pin_accepted_button = QPushButton("Pin accepted")
        pin_accepted_button.setStyleSheet("""
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
        mainContent.addWidget(pin_accepted_button)

        authorization_processing_button = QPushButton(
            "Authorization processing")
        authorization_processing_button.setStyleSheet("""
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
        mainContent.addWidget(authorization_processing_button)

        authorization_approved_button = QPushButton("Authorization approved")
        authorization_approved_button.setStyleSheet("""
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
        mainContent.addWidget(authorization_approved_button)

        card_removed_button = QPushButton("Card removed")
        card_removed_button.setStyleSheet("""
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
        mainContent.addWidget(card_removed_button)

        transaction_complete_button = QPushButton("Transaction complete")
        transaction_complete_button.setStyleSheet("""
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
        mainContent.addWidget(transaction_complete_button)

        insert_card_button.clicked.connect(
            lambda: self.send_status_signal.emit(
                TerminalStatusResponseCode.INSERT_CARD))

        card_inserted_button.clicked.connect(
            lambda: self.send_status_signal.emit(
                TerminalStatusResponseCode.CARD_INSERTED))

        card_identification_button.clicked.connect(
            lambda: self.send_status_signal.emit(
                TerminalStatusResponseCode.CARD_IDENTIFICATION))

        chip_card_accepted_button.clicked.connect(
            lambda: self.send_status_signal.emit(
                TerminalStatusResponseCode.CHIP_CARD_ACCEPTED))

        enter_pin_button.clicked.connect(
            lambda: self.send_status_signal.emit(
                TerminalStatusResponseCode.ENTER_PIN))

        pin_accepted_button.clicked.connect(
            lambda: self.send_status_signal.emit(
                TerminalStatusResponseCode.PIN_ACCEPTED))

        authorization_processing_button.clicked.connect(
            lambda: self.send_status_signal.emit(
                TerminalStatusResponseCode.AUTHORIZATION_PROCESSING))

        authorization_approved_button.clicked.connect(
            lambda: self.send_status_signal.emit(
                TerminalStatusResponseCode.AUTHORIZATION_APPROVED))

        card_removed_button.clicked.connect(
            lambda: self.send_status_signal.emit(
                TerminalStatusResponseCode.CARD_REMOVED))

        global card_details
        transaction_complete_button.clicked.connect(
            lambda: self.pay_button_clicked.emit(
                card_details
            ))

        layout.addLayout(mainContent, 2, 0)

        return widget

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
            # Disconnect signals to avoid issues
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
            except TypeError:
                # Disconnect might raise TypeError if not connected
                pass
            self.server_thread = None  # Set to None after stopping and disconnecting

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
            except TypeError:
                pass
        event.accept()
