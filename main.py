import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
import logging
import sys
from PyQt5.QtWidgets import QApplication
from ui.validator_tab import ValidatorTab

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler('dian_downloader.log'),
            logging.StreamHandler()
        ]
    )

def main():
    # Configurar logging
    setup_logging()
    
    # Crear aplicación
    app = QApplication(sys.argv)
    
    # Establecer estilo global
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f0f2f5;
        }
        QPushButton {
            background-color: #1a73e8;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px 20px;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #1557b0;
        }
        QPushButton:disabled {
            background-color: #cccccc;
        }
    """)
    
    # Crear y mostrar la ventana principal
    window = MainWindow()
    window.show()
    
    # Ejecutar la aplicación
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()