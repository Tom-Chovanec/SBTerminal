import os
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QGridLayout,
    QWidget
)


def getImagePath(name: str) -> str:
    imagePath = f'assets/images/{name}'
    if not os.path.exists(imagePath):
        print(f"ERROR: {imagePath} not found")
        return ''
    return imagePath


class MainWindow(QMainWindow):
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

        layout.addWidget(settings_button, 0, 0,
                         Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
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

        layout.addWidget(settings_button, 0, 0,
                         Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(big_logo, 0, 0, Qt.AlignmentFlag.AlignCenter)

        return widget

    def showSettingsScreen(self):
        """Switches to the settings screen."""
        self.setCentralWidget(self.createSettingsScreen())

    def showIdleScreen(self):
        """Switches back to the main idle screen."""
        self.setCentralWidget(self.createIdleScreen())


app = QApplication([])

window = MainWindow()
window.show()

app.exec()

