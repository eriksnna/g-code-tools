"""Ponto de entrada do G-Path"""
import sys, traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from ui.main_window import MainWindow

def _install_excepthook() -> None:

    def handle(exc_type, exc_value, exc_tb):
        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(detail, file=sys.stderr)
        box = QMessageBox(
            QMessageBox.Icon.Critical,
            "Erro inesperado",
            f"Ocorreu um erro e a operação não pôde continuar:\n\n{exc_value}",
        )
        box.setDetailedText(detail)
        box.exec()

    sys.excepthook = handle


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    _install_excepthook()
    window = MainWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())