# config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PDF_DIR = os.path.join(BASE_DIR, 'pdf_reports')
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# Importante: Usar TEMPLATES.html directamente
TEMPLATE_FILE = os.path.join(BASE_DIR, 'TEMPLATES.html')

BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')

# Crear directorios
for folder in [PDF_DIR, LOG_DIR]:
    os.makedirs(folder, exist_ok=True)