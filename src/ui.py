import os
from PySide6.QtGui import (
    QPainterPath,
    QPixmap,
    QFont,
    QColor,
    QPainter,
    QPen
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
    QPushButton,
    QGridLayout,
    QComboBox,
    QLineEdit,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
    QSpacerItem,
)

os.environ["QT_IM_MODULE"] = "qtvirtualkeyboard"


def getImagePath(name: str) -> str:
    imagePath = f'assets/images/{name}'
    if not os.path.exists(imagePath):
        print(f"ERROR: {imagePath} not found")
        return ''
    return imagePath


class DiamondButton(QPushButton):
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
            self.rect(), Qt.AlignmentFlag.AlignCenter, "Tap\nhere")


class MainWindow(QMainWindow):
    pay_button_clicked = Signal(dict)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("SBTerminal")
        self.setFixedSize(QSize(480, 800))
        self.setStyleSheet("background-color: #181818;")

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
        """Creates and returns the main idle screen."""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)

        logo_path = getImagePath('sb_logo.png')
        settings_image_path = getImagePath('back_arrow.png')

        # settings button
        settings_button = QPushButton()
        settings_icon = QPixmap(settings_image_path)
        settings_button.clicked.connect(self.showIdleScreen)

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

        # Diamond-shaped button
        diamond_button = DiamondButton()
        diamond_button.setFixedSize(200, 200)
        diamond_button.setStyleSheet(
            "background-color: transparent; border: none;")
        mainContent.addWidget(
            diamond_button, alignment=Qt.AlignmentFlag.AlignCenter)

        mainContent.addSpacerItem(QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        layout.addLayout(mainContent, 2, 0)

        # Bottom manual entry button
        manual_button = QPushButton("Enter details manually")
        manual_button.setFont(QFont("Kulim Park", 25))
        manual_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: black;
                border-radius: 20px;
                padding: 15px;
                margin: 20px;
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """)
        manual_button.clicked.connect(self.showManualCardDetailsScreen)
        layout.addWidget(manual_button)

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
        pay_button.clicked.connect(self.handlePayButtonClicked)
        mainContent.addWidget(
            pay_button, alignment=Qt.AlignmentFlag.AlignCenter)
        mainContent.addSpacerItem(QSpacerItem(
            20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        layout.addLayout(mainContent, 2, 0)

        return widget

    def handlePayButtonClicked(self):
        card_details = {
            "card_number": self.card_number_input.text(),
            "expiration_date": self.exp_month.text() + self.exp_year.text(),
            "cvv": self.cvv_input.text(),
            "card_issuer": self.card_dropdown.currentText()
        }
        print("handle pay button clicked")
        self.pay_button_clicked.emit(card_details)

    def showSettingsScreen(self):
        """Switches to the settings screen."""
        self.setCentralWidget(self.createSettingsScreen())

    def showIdleScreen(self):
        """Switches to the main idle screen."""
        self.setCentralWidget(self.createIdleScreen())

    def showPaymentScreen(self, price: str):
        """Switches to the payment screen."""
        self.setCentralWidget(self.createPaymentScreen(price))

    def showManualCardDetailsScreen(self):
        """Switches to the manual card details screen."""
        self.setCentralWidget(self.createManualCardDetailsScreen())
