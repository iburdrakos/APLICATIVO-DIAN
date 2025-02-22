from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QFileDialog, QLabel, QProgressDialog, QTextEdit,
                             QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import pandas as pd
import os
import logging
import time
import requests
from seleniumbase import SB

class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    error = pyqtSignal(str, str)
    finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.cufes = []
        self.folder_path = ""
        self.excel_path = ""
        self.is_running = True

    def process_cufe(self, sb, cufe):
        try:
            url = "https://catalogo-vpfe.dian.gov.co/User/SearchDocument"
            logging.info(f"Procesando CUFE: {cufe}")
            
            sb.uc_open_with_reconnect(url, 4)
            time.sleep(3)

            logging.info("Resolviendo CAPTCHA...")
            sb.uc_gui_click_captcha()
            time.sleep(4)

            input_field = "input[placeholder='Ingrese el código CUFE o UUID']"
            sb.type(input_field, cufe)
            time.sleep(2)

            sb.click("button:contains('Buscar')")
            time.sleep(5)

            current_url = sb.get_current_url()
            logging.info(f"URL capturada: {current_url}")

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
                        file.write(f"{cufe}: {download_url}\n")
                    return True
                else:
                    logging.error(f"Error al descargar el archivo PDF para el CUFE {cufe}")
                    return False
            else:
                logging.error(f"No se encontró el token en la URL para el CUFE {cufe}")
                return False

        except Exception as e:
            logging.error(f"Error procesando CUFE {cufe}: {str(e)}")
            return False

    def run(self):
        try:
            with SB(uc=True, test=True, incognito=True, locale_code="en") as sb:
                total = len(self.cufes)
                for i, cufe in enumerate(self.cufes):
                    if not self.is_running:
                        break
                        
                    success = self.process_cufe(sb, cufe)
                    if not success:
                        self.error.emit(cufe, "Error procesando CUFE")
                    
                    self.progress.emit(int((i + 1) * 100 / total))

        except Exception as e:
            self.error.emit("Sistema", str(e))
        finally:
            self.finished.emit()

    def set_data(self, cufes, folder_path, excel_path):
        self.cufes = cufes
        self.folder_path = folder_path
        self.excel_path = excel_path

    def stop(self):
        self.is_running = False

class DownloadTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.worker = DownloadWorker()
        self.worker.progress.connect(self.update_progress)
        self.worker.error.connect(self.log_error)
        self.worker.finished.connect(self.download_finished)
        self.excel_path = None
        self.folder_path = None

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Instrucciones
        instructions = QLabel(
            "Pasos:\n"
            "1. Seleccione el archivo Excel que contiene los CUFEs a descargar\n"
            "2. Elija la carpeta donde se guardarán los documentos\n"
            "3. Haga clic en 'Iniciar Descarga' para comenzar el proceso"
        )
        instructions.setStyleSheet("""
            QLabel {
                background-color: #e8f5e9;
                padding: 15px;
                border-radius: 4px;
                font-size: 13px;
                line-height: 1.4;
                margin: 10px 0;
            }
        """)
        layout.addWidget(instructions)

        # Panel de selección de Excel
        excel_section = QWidget()
        excel_layout = QVBoxLayout(excel_section)
        
        excel_header = QLabel("1. Seleccionar archivo Excel con CUFEs")
        excel_header.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.excel_btn = QPushButton('Examinar')
        self.excel_btn.clicked.connect(self.select_excel)
        self.excel_btn.setStyleSheet("""
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
        """)
        
        self.excel_label = QLabel('No se ha seleccionado archivo')
        self.excel_label.setStyleSheet("color: #666;")
        
        excel_layout.addWidget(excel_header)
        excel_layout.addWidget(self.excel_btn)
        excel_layout.addWidget(self.excel_label)

        # Panel de selección de carpeta
        folder_section = QWidget()
        folder_layout = QVBoxLayout(folder_section)
        
        folder_header = QLabel("2. Seleccionar carpeta de descarga")
        folder_header.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.folder_btn = QPushButton('Examinar')
        self.folder_btn.clicked.connect(self.select_folder)
        self.folder_btn.setStyleSheet(self.excel_btn.styleSheet())
        
        self.folder_label = QLabel('No se ha seleccionado carpeta')
        self.folder_label.setStyleSheet("color: #666;")
        
        folder_layout.addWidget(folder_header)
        folder_layout.addWidget(self.folder_btn)
        folder_layout.addWidget(self.folder_label)

        # Panel de selección
        selection_panel = QWidget()
        selection_layout = QHBoxLayout(selection_panel)
        selection_layout.addWidget(excel_section)
        selection_layout.addWidget(folder_section)

        # Área de log
        log_section = QWidget()
        log_layout = QVBoxLayout(log_section)
        
        log_header = QLabel("Log de Proceso")
        log_header.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 10px;
                font-family: monospace;
            }
        """)
        
        log_layout.addWidget(log_header)
        log_layout.addWidget(self.log_viewer)

        # Botones de control
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        
        self.start_btn = QPushButton('3. Iniciar Descarga')
        self.start_btn.clicked.connect(self.start_download)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #34a853;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 14px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #2d8746;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        self.stop_btn = QPushButton('Detener')
        self.stop_btn.clicked.connect(self.stop_download)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 14px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        control_layout.addStretch()
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()

        # Agregar todo al layout principal
        layout.addWidget(selection_panel)
        layout.addWidget(log_section)
        layout.addWidget(control_panel)

    def select_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Excel con CUFEs",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        
        if file_path:
            try:
                df = pd.read_excel(file_path, sheet_name='Token')
                self.excel_path = file_path
                self.excel_label.setText(f'Archivo: {os.path.basename(file_path)}')
                self.log_viewer.append(f"Excel cargado: {len(df)} registros encontrados")
                self.update_start_button()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al leer el archivo Excel: {str(e)}")

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Carpeta de Descarga"
        )
        
        if folder_path:
            self.folder_path = folder_path
            self.folder_label.setText(f'Carpeta: {folder_path}')
            self.log_viewer.append(f"Carpeta de descarga seleccionada: {folder_path}")
            self.update_start_button()

    def update_start_button(self):
        self.start_btn.setEnabled(bool(self.excel_path and self.folder_path))

    def start_download(self):
        try:
            df = pd.read_excel(self.excel_path, sheet_name='Token')
            cufes = df['CUFE/CUDE'].dropna().tolist()
            
            if not cufes:
                QMessageBox.warning(self, "Advertencia", "No hay CUFEs para procesar")
                return
            
            self.worker.set_data(cufes, self.folder_path, self.excel_path)
            
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.excel_btn.setEnabled(False)
            self.folder_btn.setEnabled(False)
            
            self.log_viewer.clear()
            self.log_viewer.append("Iniciando proceso de descarga...")
            
            self.worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al iniciar el proceso: {str(e)}")
            self.log_viewer.append(f"Error: {str(e)}")

    def stop_download(self):
        self.worker.stop()
        self.stop_btn.setEnabled(False)
        self.log_viewer.append("Deteniendo proceso...")

    def update_progress(self, value):
        self.log_viewer.append(f"Progreso: {value}%")

    def log_error(self, cufe, error):
        self.log_viewer.append(f"Error en CUFE {cufe}: {error}")

    def download_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.excel_btn.setEnabled(True)
        self.folder_btn.setEnabled(True)
        self.log_viewer.append("Proceso de descarga finalizado")
        QMessageBox.information(self, "Completado", "Proceso de descarga finalizado")