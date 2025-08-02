from PySide6.QtWidgets import QApplication
from overlay_ui import OverlayUI
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OverlayUI()
    window.show()
    sys.exit(app.exec())