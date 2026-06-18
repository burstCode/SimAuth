import sys
from pathlib import Path

# Ensure server/ is in sys.path so gui/* can import config, database, models, etc.
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.main_window import ServerWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SimAuth Server")
    app.setQuitOnLastWindowClosed(False)   # keep alive when window is hidden to tray

    window = ServerWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
