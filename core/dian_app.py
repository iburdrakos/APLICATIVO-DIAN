from seleniumbase import SB
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                          QPushButton, QFileDialog, QLabel, QTableWidget, 
                          QTableWidgetItem, QMessageBox, QProgressDialog, QTextEdit,
                          QDialog, QLineEdit)
from PyQt5 import QtCore
import pandas as pd
import os
import logging
import time
import requests
from pdf_processor import process_downloaded_pdfs

class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.setFixedWidth(400)
        layout = QVBoxLayout()

        self.prefix_input = QLineEdit()
        self.prefix_input.setText("FVP")
        layout.addWidget(QLabel("PREFIJO CODIGO DE VENTA:"))
        layout.addWidget(self.prefix_input)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Guardar")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        self.setLayout(layout)

class DianDownloaderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_processing = False
        self.config = {
            'prefijo_venta': 'FVP'
        }
        self.initialize_ui()
        self.setup_logging()

    def initialize_ui(self):
        self.setWindowTitle('Descargador DIAN')
        self.setGeometry(100, 100, 1200, 800)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        
        top_layout = QHBoxLayout()
        self.btn_excel = QPushButton('Seleccionar Excel con CUFEs')
        self.btn_excel.clicked.connect(self.load_excel)
        self.btn_folder = QPushButton('Seleccionar Carpeta Destino')
        self.btn_folder.clicked.connect(self.select_folder)
        self.btn_extract = QPushButton('Extraer Datos')
        self.btn_extract.clicked.connect(self.extract_data)
        self.btn_config = QPushButton('Configuración')
        self.btn_config.clicked.connect(self.show_config)
        
        top_layout.addWidget(self.btn_excel)
        top_layout.addWidget(self.btn_folder)
        top_layout.addWidget(self.btn_extract)
        top_layout.addWidget(self.btn_config)
        
        self.lbl_excel = QLabel('No se ha seleccionado archivo Excel')
        self.lbl_folder = QLabel('No se ha seleccionado carpeta destino')
        self.table = QTableWidget()
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.url_label = QLabel('URL capturada:')
        self.url_text = QTextEdit()
        self.url_text.setReadOnly(True)
        
        buttons_layout = QHBoxLayout()
        self.btn_start = QPushButton('Iniciar Proceso')
        self.btn_start.clicked.connect(self.start_process)
        self.btn_start.setEnabled(False)
        self.btn_stop = QPushButton('Detener Proceso')
        self.btn_stop.clicked.connect(self.stop_process)
        self.btn_stop.setEnabled(False)
        
        buttons_layout.addWidget(self.btn_start)
        buttons_layout.addWidget(self.btn_stop)
        
        self.status_label = QLabel('Estado: Listo')
        
        layout.addLayout(top_layout)
        layout.addWidget(self.lbl_excel)
        layout.addWidget(self.lbl_folder)
        layout.addWidget(self.table)
        layout.addWidget(self.log_viewer)
        layout.addWidget(self.url_label)
        layout.addWidget(self.url_text)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.status_label)
        
        main_widget.setLayout(layout)

    def load_excel(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Abrir Excel', '', 'Excel files (*.xlsx *.xls)')
        if fname:
            try:
                df = pd.read_excel(fname, sheet_name='Token')
                self.excel_path = fname
                self.lbl_excel.setText(f'Archivo: {fname}')
                self.update_table(df)
                if hasattr(self, 'folder_path'):
                    self.btn_start.setEnabled(True)
                logging.info(f"Excel cargado: {fname}")
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Error al cargar Excel: {str(e)}')
                logging.error(f"Error cargando Excel: {str(e)}")

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Seleccionar Carpeta Destino')
        if folder:
            self.folder_path = folder
            self.lbl_folder.setText(f'Carpeta: {folder}')
            if hasattr(self, 'excel_path'):
                self.btn_start.setEnabled(True)
            logging.info(f"Carpeta destino seleccionada: {folder}")

    def update_table(self, df):
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(df.columns)
        
        for i in range(len(df)):
            for j in range(len(df.columns)):
                item = QTableWidgetItem(str(df.iloc[i, j]))
                self.table.setItem(i, j, item)

    def show_config(self):
        dialog = ConfigDialog(self)
        dialog.prefix_input.setText(self.config['prefijo_venta'])
        
        if dialog.exec_():
            self.config = {
                'prefijo_venta': dialog.prefix_input.text()
            }
            logging.info("Configuración actualizada")

    def setup_logging(self):
        class QTextEditLogger(logging.Handler):
            def __init__(self, widget):
                super().__init__()
                self.widget = widget

            def emit(self, record):
                msg = self.format(record)
                self.widget.append(msg)
                
        self.log_handler = QTextEditLogger(self.log_viewer)
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        logger = logging.getLogger()
        logger.addHandler(self.log_handler)
        logger.setLevel(logging.INFO)

    def process_cufe(self, sb, cufe):
        try:
            url = "https://catalogo-vpfe.dian.gov.co/User/SearchDocument"
            logging.info(f"Procesando CUFE: {cufe}")
            
            sb.uc_open_with_reconnect(url, 4)
            time.sleep(3)

            logging.info("Resolviendo primer CAPTCHA...")
            max_captcha_attempts = 3
            for captcha_attempt in range(max_captcha_attempts):
                try:
                    sb.uc_gui_click_captcha()
                    time.sleep(4)
                    break
                except Exception as e:
                    if captcha_attempt == max_captcha_attempts - 1:
                        raise Exception(f"No se pudo resolver el primer CAPTCHA después de {max_captcha_attempts} intentos")
                    logging.warning(f"Error resolviendo el primer CAPTCHA (Intento {captcha_attempt+1}): {str(e)}")
                    time.sleep(2)

            input_field = "input[placeholder='Ingrese el código CUFE o UUID']"
            sb.type(input_field, cufe)
            time.sleep(2)

            sb.click("button:contains('Buscar')")
            time.sleep(5)

            current_url = sb.get_current_url()
            logging.info(f"URL capturada: {current_url}")
            self.current_url = current_url
            self.url_text.setText(current_url)

            with open("urls.txt", "a") as file:
                file.write(f"{cufe}: {current_url}\n")

            token = None
            if "Token=" in current_url:
                token = current_url.split("Token=")[1].split("&")[0]
            elif "token=" in current_url:
                token = current_url.split("token=")[1].split("&")[0]

            if token:
                download_url = f"https://catalogo-vpfe.dian.gov.co/Document/DownloadPDF?trackId={cufe}&token={token}"
                response = requests.get(download_url)
                
                if response.status_code == 200:
                    excel_name = os.path.splitext(os.path.basename(self.excel_path))[0]
                    filename = f"{excel_name}_{cufe}.pdf"
                    filepath = os.path.join(self.folder_path, filename)
                    with open(filepath, "wb") as file:
                        file.write(response.content)
                    logging.info(f"Archivo PDF descargado: {filename}")
                    
                    with open(os.path.join(self.folder_path, "links_descarga.txt"), "a") as file:
                        file.write(download_url + "\n")
                else:
                    logging.error(f"Error al descargar el archivo PDF para el CUFE {cufe}")
            else:
                logging.error(f"No se encontró el token en la URL para el CUFE {cufe}")

            return True

        except Exception as e:
            logging.error(f"Error procesando CUFE {cufe}: {str(e)}")
            return False

    def stop_process(self):
        self.is_processing = False
        self.status_label.setText('Estado: Deteniendo proceso...')
        self.btn_stop.setEnabled(False)
        logging.info("Proceso detenido por el usuario")

    def start_process(self):
        try:
            self.is_processing = True
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            
            df = pd.read_excel(self.excel_path, sheet_name='Token')
            cufes = df['CUFE/CUDE'].dropna().tolist()

            progress = QProgressDialog("Procesando documentos...", "Cancelar", 0, len(cufes), self)
            progress.setWindowModality(QtCore.Qt.WindowModal)

            excel_name = os.path.splitext(os.path.basename(self.excel_path))[0]

            with open(os.path.join(self.folder_path, "links_descarga.txt"), "w") as file:
                pass

            with SB(uc=True, test=True, incognito=True, locale_code="en") as sb:
                for i, cufe in enumerate(cufes):
                    if not self.is_processing:
                        break

                    success = self.process_cufe(sb, cufe)
                    progress.setValue(i + 1)
                    self.status_label.setText(f'Estado: Procesado {i+1} de {len(cufes)}')
                    QApplication.processEvents()

                    if progress.wasCanceled():
                        self.is_processing = False
                        break

            progress.close()
            
            if not self.is_processing:
                QMessageBox.information(self, "Detenido", "Proceso detenido por el usuario")
            else:
                QMessageBox.information(self, "Completado", "Proceso finalizado exitosamente")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error en el proceso: {str(e)}")
            logging.error(f"Error en proceso principal: {str(e)}")
        finally:
            self.is_processing = False
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.status_label.setText('Estado: Listo')

    def extract_data(self):
        if hasattr(self, 'folder_path') and hasattr(self, 'excel_path'):
            process_downloaded_pdfs(self.folder_path, self.excel_path, self.config['prefijo_venta'])
            QMessageBox.information(self, "Completado", "Extracción de datos finalizada exitosamente")
        else:
            QMessageBox.warning(self, "Advertencia", "Seleccione primero la carpeta de destino y el archivo Excel")

def main():
    app = QApplication([])
    window = DianDownloaderGUI()
    window.show()
    app.exec_()

if __name__ == '__main__':
    main()