# utils.py
import os
from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML
from io import BytesIO
from django.core.files import File

def generate_invoice(order):
    # Render invoice HTML template
    html_string = render_to_string('payments/invoice.html', {'order': order})
    
    # Create a PDF file in memory
    pdf_file = BytesIO()
    HTML(string=html_string).write_pdf(target=pdf_file)
    
    # Save PDF to order.invoice
    pdf_file.seek(0)
    filename = f"invoice_order_{order.id}.pdf"
    order.invoice.save(filename, File(pdf_file))
    return order.invoice
