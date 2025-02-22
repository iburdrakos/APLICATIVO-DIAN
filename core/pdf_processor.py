# Importaciones estándar
import os
import re
import pandas as pd
from collections import defaultdict

# Importaciones para PDF
import pdfplumber
from PyPDF2 import PdfReader

# Importaciones PyQt5
from PyQt5.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QPushButton,
    QFileDialog, 
    QLabel, 
    QProgressDialog,
    QTableWidget,
    QTableWidgetItem, 
    QMessageBox, 
    QTabWidget,
    QComboBox,
    QHeaderView,
    QApplication
)
from PyQt5.QtCore import Qt



# Constantes y configuración global
COLUMN_HEADERS = {
   "A": "Razón Social",
    "B": "Tipo Documento",
    "C": "Prefijo",
    "D": "Número Documento",
    "E": "Fecha",
    "F": "Indicador IVA",
    "G": "Concepto",
    "H": "Cantidad",
    "I": "Unidad Medida",
    "J": "Base Gravable",
    "K": "Porcentaje IVA",
    "L": "NIT",
    "M": "Número Factura",
    "N": "Fecha Factura",
    "O": "Número Control",
    "P": "Total IVA",
    "Q": "Total INC",
    "R": "Total Bolsas",
    "S": "Otros Impuestos",
    "T": "IBUA",
    "U": "ICUI",
    "V": "Rete Fuente",
    "W": "Rete IVA",
    "X": "Rete ICA"
}


def get_invoice_type(filename, pdf_path, user_selected_type, prefijo_venta):
    """Determina el tipo de factura basado en la selección del usuario"""
    # Mapear tipos de documento con sus códigos internos
    type_mapping = {
        'Factura de Venta': 'factura_venta',
        'Factura de Compra': 'factura_compra',
        'Nota Crédito': 'nota_credito',
        'Nota Débito': 'nota_debito',
        'Facturas de Compras Nuevos': 'facturas_compras_nuevos',
        'Facturas de Gastos': 'facturas_gastos'
    }
    
    # Retornar el tipo de documento seleccionado por el usuario
    return type_mapping.get(user_selected_type)

def get_document_type(filepath):
    """Determina el tipo de documento basado en el contenido del archivo"""
    try:
        with pdfplumber.open(filepath) as pdf:
            text = pdf.pages[0].extract_text()
            
            # Verificar el tipo de documento basado en el texto
            if "Factura Electrónica de Venta" in text:
                return "Factura de Venta"
            elif "Nota Crédito de la Factura Electrónica" in text:
                return "Nota Crédito"
            elif "Nota Débito de la Factura Electrónica" in text:
                return "Nota Débito"
            elif "Factura de Compra Electrónica" in text:
                return "Factura de Compra"
            elif "Factura de Gastos" in text:
                return "Facturas de Gastos"
            elif "Compras Nuevos" in text:
                return "Facturas de Compras Nuevos"
            
            # Si no se puede determinar, retornar None
            return None
            
    except Exception as e:
        print(f"Error determinando tipo de documento: {str(e)}")
        return None

# Funciones auxiliares
def get_iva_indicator(iva_value):
    """Determina el indicador IVA basado en el valor del IVA o tipo de impuesto"""
    try:
        # Para valores numéricos de IVA
        if isinstance(iva_value, (int, float)) or iva_value.replace('.', '').isdigit():
            iva = float(iva_value)
            if iva == 19:
                return "001"
            elif iva == 5:
                return "002"
            elif iva == 0:
                return "003"
            elif iva in [4, 8, 16]:
                return "004"  # INC-IPO-ICO
        
        # Para campos especiales que vienen del documento
        if 'IBUA' in str(iva_value).upper():
            return str(iva_value)  # Retorna el valor directo de IBUA
        elif 'ICUI' in str(iva_value).upper():
            return str(iva_value)  # Retorna el valor directo de ICUI
        elif 'OTROS IMPUESTOS' in str(iva_value).upper():
            return str(iva_value)  # Retorna el valor directo de Otros Impuestos
        
        return ""
    except (ValueError, TypeError):
        return ""

def parse_colombian_number(text):
    """Convierte un número en formato colombiano a float"""
    try:
        # Si el texto está vacío o es None, retornar 0
        if not text or text.isspace():
            return 0.0
            
        # Remover el símbolo de peso y espacios
        clean_text = text.replace('$', '').replace(' ', '')
        
        # Si después de limpiar está vacío, retornar 0
        if not clean_text:
            return 0.0
            
        if '.' in clean_text and ',' not in clean_text:
            clean_text = clean_text.replace('.', '')
            return float(clean_text)
        
        parts = clean_text.split(',')
        if len(parts) > 1:
            integer_part = parts[0].replace('.', '')
            decimal_part = parts[1][:2]
            return float(f"{integer_part}.{decimal_part}")
        else:
            return float(clean_text.replace('.', ''))
    except (ValueError, AttributeError):
        print(f"No se pudo convertir el valor: '{text}'")
        return 0.0
        

def extract_field(text, start_marker, end_marker):
    """Extrae un campo específico del texto entre dos marcadores"""
    try:
        start_index = text.find(start_marker)
        if start_index == -1:
            return ""
        start_index += len(start_marker)
        
        end_index = text.find(end_marker, start_index)
        if end_index == -1:
            return text[start_index:].strip()
            
        return text[start_index:end_index].strip()
    except Exception:
        return ""

def extract_total_impuestos(pdf):
    """Extrae los impuestos totales del documento"""
    impuestos = {
        'Total IVA': 0.00,
        'Total INC': 0.00,
        'Total Bolsas': 0.00,
        'IBUA': 0.00,
        'ICUI': 0.00,  # Agregado ICUI
        'Otros Impuestos': 0.00,
        'Rete Fuente': 0.00,
        'Rete IVA': 0.00,
        'Rete ICA': 0.00
    }
    
    try:
        datos_totales_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if "Datos Totales" in text:
                datos_totales_text = text[text.find("Datos Totales"):]
                break
        
        if datos_totales_text:
            patrones = {
                'Total IVA': [r'IVA\s*[\$\s]*([0-9.,]+)'],
                'Total INC': [r'INC\s*[\$\s]*([0-9.,]+)'],
                'Total Bolsas': [r'Bolsas\s*[\$\s]*([0-9.,]+)'],
                'IBUA': [r'IBUA\s*[\$\s]*([0-9.,]+)'],
                'ICUI': [r'ICUI\s*[\$\s]*([0-9.,]+)'],  # Patrón específico para ICUI
                'Otros Impuestos': [r'Otros impuestos\s*[\$\s]*([0-9.,]+)'],
                'Rete Fuente': [r'Rete fuente\s*[\$\s]*([0-9.,]+)'],
                'Rete IVA': [r'Rete IVA\s*[\$\s]*([0-9.,]+)'],
                'Rete ICA': [r'Rete ICA\s*[\$\s]*([0-9.,]+)']
            }
            
            for impuesto, lista_patrones in patrones.items():
                for patron in lista_patrones:
                    match = re.search(patron, datos_totales_text, re.IGNORECASE)  # Agregado IGNORECASE
                    if match:
                        valor_str = match.group(1).strip()
                        try:
                            valor = parse_colombian_number(valor_str)
                            impuestos[impuesto] = valor
                            break
                        except Exception as e:
                            print(f"Error convirtiendo valor para {impuesto}: {valor_str} - {str(e)}")
                            
            # Debug: imprimir el texto encontrado
            print("Datos Totales encontrados:", datos_totales_text)
            print("Impuestos extraídos:", impuestos)
            
    except Exception as e:
        print(f"Error extrayendo impuestos: {str(e)}")
    
    return impuestos

def create_base_row(emisor, tipo_documento, numero_documento, fecha_emision, numero_factura, iva_percent, base_iva, impuestos):
    """Crea una fila base con todos los valores"""
    row = {
        "A": emisor,
        "B": tipo_documento,
        "C": "",
        "D": numero_documento,
        "E": fecha_emision,
        "F": get_iva_indicator(iva_percent),
        "G": "PRINCIPAL",
        "H": "1",
        "I": "UNIDAD",
        "J": f"{base_iva:.2f}",
        "K": str(iva_percent),
        "L": numero_documento,
        "M": numero_factura,
        "N": fecha_emision,
        "O": numero_factura,
        "P": str(impuestos['Total IVA']),
        "Q": str(impuestos['Total INC']),
        "R": str(impuestos['Total Bolsas']),
        "S": str(impuestos['Otros Impuestos']),  # Valor directo de Otros Impuestos
        "T": str(impuestos['IBUA']), 
        "U": str(impuestos['ICUI']),            # Valor directo de IBUA
        "V": str(impuestos['Rete Fuente']),
        "W": str(impuestos['Rete IVA']),
        "X": str(impuestos['Rete ICA'])
    }
    return row


    
# Funciones de procesamiento principales
def process_factura_venta(pdf_path):
    """Procesa una factura de venta"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            text = first_page.extract_text()
            
            emisor = extract_field(text, "Razón Social:", "Nombre Comercial:")
            numero_documento = extract_field(text, "Nit del Emisor:", "País:")
            fecha_emision = extract_field(text, "Fecha de Emisión:", "Medio de Pago:")
            numero_factura = extract_field(text, "Número de Factura:", "Forma de pago:")
            
            impuestos = extract_total_impuestos(pdf)
            
            sumas_por_iva = defaultdict(float)
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or len(row) < 10:
                            continue
                        row = [str(cell).strip() if cell is not None else '' for cell in row]
                        if row[0].strip().isdigit():
                            try:
                                precio_unitario = parse_colombian_number(row[5])
                                iva_percent = float(row[9].replace(',', '.'))
                                sumas_por_iva[iva_percent] += precio_unitario
                            except Exception as e:
                                print(f"Error procesando fila: {str(e)}")
                                continue
            
            rows = []
            for iva_percent, base_iva in sumas_por_iva.items():
                row = create_base_row(
                    emisor=emisor,
                    tipo_documento="Factura de Venta",
                    numero_documento=numero_documento,
                    fecha_emision=fecha_emision,
                    numero_factura=numero_factura,
                    iva_percent=iva_percent,
                    base_iva=base_iva,
                    impuestos=impuestos
                )
                rows.append(row)
            
            return rows
            
    except Exception as e:
        print(f"Error procesando factura de venta: {str(e)}")
        return None

def process_factura_compra(pdf_path):
    """Procesa una factura de compra"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            text = first_page.extract_text()
            
            nombre_comprador = extract_field(text, "Nombre o Razón Social:", "Tipo de Documento:")
            numero_documento = extract_field(text, "Nit del Emisor:", "País:")
            fecha_emision = extract_field(text, "Fecha de Emisión:", "Medio de Pago:")
            numero_factura = extract_field(text, "Número de Factura:", "Forma de pago:")
            
            impuestos = extract_total_impuestos(pdf)
            
            sumas_por_iva = defaultdict(float)
            suma_descuentos_detalle = 0
            iva_asumido = 0
            tiene_descuento = False
            
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or len(row) < 10:
                            continue
                        row = [str(cell).strip() if cell is not None else '' for cell in row]
                        if row[0].strip().isdigit():
                            try:
                                precio_unitario = parse_colombian_number(row[5])
                                iva_percent = float(row[9].replace(',', '.'))
                                descuento = parse_colombian_number(row[6]) if row[6] else 0
                                
                                sumas_por_iva[iva_percent] += precio_unitario
                                if descuento > 0:
                                    suma_descuentos_detalle += descuento
                                    tiene_descuento = True
                                    
                            except Exception as e:
                                print(f"Error procesando fila: {str(e)}")
                                continue
                        elif len(row) >= 4 and "IVA ASUMIDO" in str(row[3]):
                            try:
                                iva_asumido = parse_colombian_number(row[5])
                                tiene_descuento = True
                            except Exception as e:
                                print(f"Error procesando IVA ASUMIDO: {str(e)}")
            
            rows = []
            for iva_percent, base_iva in sumas_por_iva.items():
                row = create_base_row(
                    emisor=nombre_comprador,
                    tipo_documento="Factura de Compra",
                    numero_documento=numero_documento,
                    fecha_emision=fecha_emision,
                    numero_factura=numero_factura,
                    iva_percent=iva_percent,
                    base_iva=base_iva,
                    impuestos=impuestos
                )
                rows.append(row)
            
            # Procesar descuentos si existen
            descuento_rows = []
            if tiene_descuento:
                valor_descuento = suma_descuentos_detalle if suma_descuentos_detalle > 0 else iva_asumido
                descuento_row = create_base_row(
                    emisor=nombre_comprador,
                    tipo_documento="Factura de Compra",
                    numero_documento=numero_documento,
                    fecha_emision=fecha_emision,
                    numero_factura=numero_factura,
                    iva_percent=0,
                    base_iva=valor_descuento,
                    impuestos=impuestos
                )
                descuento_row.update({
                    "F": "42104001",
                    "G": str(valor_descuento),
                    "H": "0"
                })
                descuento_rows.append(descuento_row)
            
            return rows, descuento_rows
            
    except Exception as e:
        print(f"Error procesando factura de compra: {str(e)}")
        return None, []

# Funciones similares para los otros tipos de documentos
def process_nota_credito(pdf_path):
    """Procesa una nota crédito"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Lógica similar a process_factura_venta pero con tipo_documento="Nota Crédito"
            # ...
            pass
    except Exception as e:
        print(f"Error procesando nota crédito: {str(e)}")
        return None

def process_nota_debito(pdf_path):
    """Procesa una nota débito"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Lógica similar a process_factura_venta pero con tipo_documento="Nota Débito"
            # ...
            pass
    except Exception as e:
        print(f"Error procesando nota débito: {str(e)}")
        return None

def process_facturas_compras_nuevos(pdf_path):
    """Procesa una factura de compras nuevos"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Lógica similar a process_factura_compra
            # ...
            pass
    except Exception as e:
        print(f"Error procesando facturas de compras nuevos: {str(e)}")
        return None


def process_facturas_gastos(pdf_path):
    """Procesa una factura de gastos"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            text = first_page.extract_text()
            
            nombre_comprador = extract_field(text, "Nombre o Razón Social:", "Tipo de Documento:")
            numero_documento = extract_field(text, "Nit del Emisor:", "País:")
            fecha_emision = extract_field(text, "Fecha de Emisión:", "Medio de Pago:")
            numero_factura = extract_field(text, "Número de Factura:", "Forma de pago:")
            
            impuestos = extract_total_impuestos(pdf)
            
            sumas_por_iva = defaultdict(float)
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or len(row) < 10:
                            continue
                        row = [str(cell).strip() if cell is not None else '' for cell in row]
                        if row[0].strip().isdigit():
                            try:
                                precio_unitario = parse_colombian_number(row[5])
                                iva_percent = float(row[9].replace(',', '.'))
                                sumas_por_iva[iva_percent] += precio_unitario
                            except Exception as e:
                                print(f"Error procesando fila: {str(e)}")
                                continue
            
            rows = []
            for iva_percent, base_iva in sumas_por_iva.items():
                row = create_base_row(
                    emisor=nombre_comprador,
                    tipo_documento="Facturas de Gastos",
                    numero_documento=numero_documento,
                    fecha_emision=fecha_emision,
                    numero_factura=numero_factura,
                    iva_percent=iva_percent,
                    base_iva=base_iva,
                    impuestos=impuestos
                )
                rows.append(row)
            
            return rows
            
    except Exception as e:
        print(f"Error procesando facturas de gastos: {str(e)}")
        return None

def process_inventory(pdf_path):
    """Procesa el inventario de un documento PDF"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            text = first_page.extract_text()
            
            nit_emisor = extract_field(text, "Nit del Emisor:", "País:")
            numero_factura = extract_field(text, "Número de Factura:", "Forma de pago:")
            
            inventory_items = []
            
            for page in pdf.pages:
                tables = page.extract_tables()
                
                for table in tables:
                    for row in table:
                        if not row or len(row) < 11:
                            continue
                            
                        row = [str(cell).strip() if cell is not None else '' for cell in row]
                        
                        if row[0].strip().isdigit():
                            try:
                                item = {
                                    "nit_emisor": nit_emisor,
                                    "numero_factura": numero_factura,
                                    "Nro": row[0],
                                    "Codigo": row[1],
                                    "Descripcion": row[2],
                                    "U/M": row[3],
                                    "Cantidad": parse_colombian_number(row[4]),
                                    "Precio_unitario": parse_colombian_number(row[5].replace('$', '')),
                                    "Descuento": parse_colombian_number(row[6].replace('$', '')),
                                    "Recargo": parse_colombian_number(row[7].replace('$', '')),
                                    "IVA": parse_colombian_number(row[8].replace('$', '')),
                                    "Porcentaje_IVA": float(row[9].replace('%', '').strip() or '0'),
                                    "INC": parse_colombian_number(row[10].replace('$', '')),
                                    "Porcentaje_INC": float(row[11].replace('%', '').strip() or '0'),
                                    "Precio_venta": parse_colombian_number(row[12].replace('$', ''))
                                }
                                inventory_items.append(item)
                            except Exception as e:
                                print(f"Error procesando línea de inventario: {row}")
                                print(f"Error: {str(e)}")
                                continue
            
            return inventory_items
            
    except Exception as e:
        print(f"Error procesando inventario: {str(e)}")
        return None

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

    def setup_tables(self):
        """Configura las tablas para mostrar resultados"""
        # Lista de encabezados en orden
        self.column_headers = [
            "Razón Social",
            "Tipo Documento",
            "Prefijo",
            "Número Documento",
            "Fecha",
            "Indicador IVA",
            "Concepto",
            "Cantidad",
            "Unidad Medida",
            "Base Gravable",
            "Porcentaje IVA",
            "NIT",
            "Número Factura",
            "Fecha Factura",
            "Número Control",
            "Total IVA",
            "Total INC",
            "Total Bolsas",
            "Otros Impuestos",
            "ICUI",
            "Rete Fuente",
            "Rete IVA",
            "Rete ICA"
        ]

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
            # Configurar columnas y encabezados
            table.setColumnCount(len(self.column_headers))
            table.setHorizontalHeaderLabels(self.column_headers)
            
            # Otras configuraciones de la tabla
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setAlternatingRowColors(True)
            
            header = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeToContents)
            header.setStretchLastSection(True)
            
            # Estilo para la tabla y encabezados
            table.setStyleSheet("""
                QTableWidget {
                    gridline-color: #ccc;
                    background-color: white;
                    alternate-background-color: #f5f5f5;
                }
                QHeaderView::section {
                    background-color: #f0f0f0;
                    padding: 6px;
                    border: 1px solid #ccc;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)
            
            self.tab_widget.addTab(table, name.capitalize())

   

    
    