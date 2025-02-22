from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QFileDialog, QLabel, QProgressDialog, QTableWidget,
                            QTableWidgetItem, QMessageBox, QTabWidget, QComboBox,
                            QHeaderView)
from PyQt5.QtCore import Qt
import pandas as pd
import os
from PyPDF2 import PdfReader
from core.pdf_processor import (process_factura_venta, process_factura_compra,
                             process_nota_credito, process_nota_debito,
                             process_facturas_compras_nuevos, process_facturas_gastos,
                             process_inventory, get_document_type, COLUMN_HEADERS)
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QFileDialog, QLabel, QProgressDialog, QTableWidget,
                             QTableWidgetItem, QMessageBox, QTabWidget, QComboBox,
                             QHeaderView, QApplication)  #
class ValidatorTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.files_to_process = []
        self.current_type = None
        self.setup_data_containers()

    def setup_data_containers(self):
        """Inicializa los contenedores de datos"""
        self.processed_data = {
            'venta': [],
            'compra': [],
            'credito': [],
            'debito': [],
            'errores': [],
            'inventario': [],
            'descuentos': [],
            'compras_nuevos': [],
            'gastos': []
        }

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Sección de instrucciones
        instructions = QLabel(
            "Pasos a seguir:\n"
            "1. Seleccione los archivos PDF a procesar\n"
            "2. Elija el tipo de documento\n"
            "3. Haga clic en 'Procesar Documentos'"
        )
        instructions.setStyleSheet("""
            QLabel {
                padding: 10px;
                background: #f0f0f0;
                border-radius: 5px;
                font-size: 14px;
                margin: 10px 0;
            }
        """)
        layout.addWidget(instructions)

        # Panel superior
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)

        # Botón seleccionar archivos
        self.select_btn = QPushButton('1. Seleccionar PDFs')
        self.select_btn.clicked.connect(self.select_files)
        self.select_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 14px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
        """)

        # Selector de tipo de documento
        doc_type_widget = QWidget()
        doc_type_layout = QHBoxLayout(doc_type_widget)
        doc_type_label = QLabel("2. Tipo de documento:")
        doc_type_label.setStyleSheet("font-size: 14px;")
        
        self.doc_type_combo = QComboBox()
        self.doc_type_combo.addItems([
            'Factura de Venta',
            'Factura de Compra',
            'Nota Crédito',
            'Nota Débito',
            'Facturas de Compras Nuevos',
            'Facturas de Gastos'
        ])
        self.doc_type_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
                min-width: 200px;
                font-size: 14px;
            }
        """)
        
        doc_type_layout.addWidget(doc_type_label)
        doc_type_layout.addWidget(self.doc_type_combo)

        # Botón de procesar
        self.process_btn = QPushButton('3. Procesar Documentos')
        self.process_btn.clicked.connect(self.process_files)
        self.process_btn.setEnabled(False)
        self.process_btn.setStyleSheet("""
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

        top_layout.addWidget(self.select_btn)
        top_layout.addWidget(doc_type_widget)
        top_layout.addWidget(self.process_btn)
        top_layout.addStretch()

        # Etiqueta de archivos seleccionados
        self.files_label = QLabel('No hay archivos seleccionados')
        self.files_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #666;
                margin: 10px 0;
            }
        """)
        
        # TabWidget para resultados
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                background: white;
            }
            QTabBar::tab {
                background: #f0f0f0;
                border: 1px solid #ccc;
                padding: 5px 10px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
            }
        """)
        self.setup_tables()

        # Panel inferior
        bottom_panel = QWidget()
        bottom_layout = QHBoxLayout(bottom_panel)

        self.export_btn = QPushButton('Exportar a Excel')
        self.export_btn.clicked.connect(self.export_to_excel)
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet("""
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

        bottom_layout.addStretch()
        bottom_layout.addWidget(self.export_btn)

        # Agregar todo al layout principal
        layout.addWidget(top_panel)
        layout.addWidget(self.files_label)
        layout.addWidget(self.tab_widget)
        layout.addWidget(bottom_panel)

    def setup_tables(self):
        """Configura las tablas para mostrar resultados"""
        self.tables = {
            'venta': QTableWidget(),
            'compra': QTableWidget(),
            'credito': QTableWidget(),
            'debito': QTableWidget(),
            'errores': QTableWidget(),
            'inventario': QTableWidget(),
            'descuentos': QTableWidget(),
            'compras_nuevos': QTableWidget(),
            'gastos': QTableWidget()
        }

        for name, table in self.tables.items():
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setAlternatingRowColors(True)
            header = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeToContents)
            header.setStretchLastSection(True)
            table.setStyleSheet("""
                QTableWidget {
                    gridline-color: #ccc;
                    background-color: white;
                    alternate-background-color: #f5f5f5;
                }
                QHeaderView::section {
                    background-color: #f0f0f0;
                    padding: 4px;
                    border: 1px solid #ccc;
                    font-weight: bold;
                }
            """)
            self.tab_widget.addTab(table, name.capitalize())

    def select_files(self):
        """Permite al usuario seleccionar archivos PDF"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleccionar PDFs a procesar",
            "",
            "PDF Files (*.pdf)"
        )
        
        if files:
            self.files_to_process = files
            self.files_label.setText(f'Archivos seleccionados: {len(files)}')
            self.process_btn.setEnabled(True)

    def process_files(self):
        """Procesa los archivos PDF seleccionados"""
        if not self.files_to_process:
            QMessageBox.warning(self, "Advertencia", "No hay archivos para procesar")
            return

        # Obtener el tipo de documento seleccionado
        doc_type = self.doc_type_combo.currentText()
        processor_map = {
            'Factura de Venta': process_factura_venta,
            'Factura de Compra': process_factura_compra,
            'Nota Crédito': process_nota_credito,
            'Nota Débito': process_nota_debito,
            'Facturas de Compras Nuevos': process_facturas_compras_nuevos,
            'Facturas de Gastos': process_facturas_gastos
        }

        processor = processor_map.get(doc_type)
        if not processor:
            QMessageBox.warning(self, "Error", "Tipo de documento no válido")
            return

        # Configurar barra de progreso
        progress = QProgressDialog("Procesando documentos...", "Cancelar", 0, len(self.files_to_process), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Procesando")
        progress.setMinimumDuration(0)
        progress.setMinimumWidth(400)

        processed = 0
        errors = 0

        # Mapeo de tipos de documento a claves de processed_data
        type_to_key = {
            'Factura de Venta': 'venta',
            'Factura de Compra': 'compra',
            'Nota Crédito': 'credito',
            'Nota Débito': 'debito',
            'Facturas de Compras Nuevos': 'compras_nuevos',
            'Facturas de Gastos': 'gastos'
        }

        # Procesar cada archivo
        for i, filepath in enumerate(self.files_to_process):
            if progress.wasCanceled():
                break

            progress.setValue(i)
            filename = os.path.basename(filepath)
            progress.setLabelText(f"Procesando {i+1} de {len(self.files_to_process)}: {filename}")

            try:
                # Procesamiento basado en el tipo de documento
                if doc_type == 'Factura de Compra':
                    rows, descuentos = processor(filepath)
                    inventory_items = process_inventory(filepath)
                    
                    if rows:
                        self.processed_data['compra'].extend(rows)
                        if descuentos:
                            self.processed_data['descuentos'].extend(descuentos)
                        if inventory_items:
                            self.processed_data['inventario'].extend(inventory_items)
                        processed += 1
                    else:
                        self.processed_data['errores'].append({
                            'Archivo': filename,
                            'Tipo': doc_type,
                            'Error': 'No se pudo procesar'
                        })
                        errors += 1
                else:
                    # Para todos los demás tipos de documento
                    rows = processor(filepath)
                    if rows:
                        # Usar el mapeo de tipos a claves
                        key = type_to_key.get(doc_type)
                        if key:
                            self.processed_data[key].extend(rows)
                            processed += 1
                        else:
                            self.processed_data['errores'].append({
                                'Archivo': filename,
                                'Tipo': doc_type,
                                'Error': 'Tipo de documento no reconocido'
                            })
                            errors += 1
                    else:
                        self.processed_data['errores'].append({
                            'Archivo': filename,
                            'Tipo': doc_type,
                            'Error': 'No se pudo procesar'
                        })
                        errors += 1

            except Exception as e:
                self.processed_data['errores'].append({
                    'Archivo': filename,
                    'Tipo': doc_type,
                    'Error': str(e)
                })
                errors += 1
                import traceback
                traceback.print_exc()  # Imprimir el traceback completo

            # Actualizar progreso después de cada archivo
            QApplication.processEvents()

        progress.setValue(len(self.files_to_process))
        
        # Actualizar tablas y habilitar exportación
        self.update_tables()
        self.export_btn.setEnabled(True)
        
        # Mostrar resumen
        QMessageBox.information(self, "Completado", 
            f"Proceso finalizado:\n"
            f"Total archivos: {len(self.files_to_process)}\n"
            f"Procesados exitosamente: {processed}\n"
            f"Errores: {errors}"
        )

    def update_tables(self):
        """Actualiza las tablas con los datos procesados"""
        for data_type, data in self.processed_data.items():
            if data:
                table = self.tables[data_type]
                
                # Usar los headers definidos en el procesador
                headers = list(COLUMN_HEADERS.values())
                
                # Configurar tabla
                table.setColumnCount(len(headers))
                table.setHorizontalHeaderLabels(headers)
                table.setRowCount(len(data))
                
                for i, row in enumerate(data):
                    # Convertir el diccionario de datos a un formato que coincida con los headers
                    for j, (letra, nombre) in enumerate(COLUMN_HEADERS.items()):
                        if letra == 'T':  # Para la columna ICUI
                            value = str(row.get('ICUI', row.get('T', '0.0')))
                        else:
                            value = str(row.get(letra, '0.0'))
                        item = QTableWidgetItem(value)
                        table.setItem(i, j, item)
                
                table.resizeColumnsToContents()
        
    def export_to_excel(self):
        """Exporta los datos procesados a Excel"""
        if not any(self.processed_data.values()):
            QMessageBox.warning(self, "Advertencia", "No hay datos para exportar")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Excel",
            "",
            "Excel Files (*.xlsx)"
        )
        
        if file_path:
            try:
                headers = [
                    "Razón Social", "Tipo Documento", "Prefijo", "Número Documento",
                    "Fecha", "Indicador IVA", "Concepto", "Cantidad", "Unidad Medida",
                    "Base Gravable", "Porcentaje IVA", "NIT", "Número Factura",
                    "Fecha Factura", "Número Control", "Total IVA", "Total INC",
                    "Total Bolsas", "Otros Impuestos", "ICUI", "Rete Fuente",
                    "Rete IVA", "Rete ICA"
                ]
                
                with pd.ExcelWriter(file_path) as writer:
                    for sheet_name, data in self.processed_data.items():
                        if data:
                            # Convertir a DataFrame manteniendo el orden de las columnas
                            df = pd.DataFrame(data)
                            # Renombrar columnas usando el mapeo A->nombre, B->nombre, etc.
                            df.columns = headers[:len(df.columns)]
                            df.to_excel(writer, sheet_name=sheet_name.capitalize(), index=False)
                
                QMessageBox.information(self, "Éxito", "Datos exportados correctamente")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al exportar: {str(e)}")