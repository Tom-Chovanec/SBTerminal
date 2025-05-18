from terminal_config import config
from ui import MainWindow

from PySide6.QtWidgets import QApplication


def main() -> None:
    global config
    app = QApplication([])

    window = MainWindow()

    window.show()

    app.exec()


if __name__ == "__main__":
    main()
