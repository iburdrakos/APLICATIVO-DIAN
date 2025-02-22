from .pdf_processor import (
    process_factura_venta,
    process_factura_compra,
    process_facturas_compras_nuevos,
    process_facturas_gastos,
    process_nota_credito,
    process_nota_debito,
    process_inventory
)

__all__ = [
    'process_factura_venta',
    'process_factura_compra',
    'process_facturas_compras_nuevos',
    'process_facturas_gastos',
    'process_nota_credito',
    'process_nota_debito',
    'process_inventory'
]