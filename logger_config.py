# logger_config.py
import os
import logging
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# Crear directorios
for folder in ['payment', 'email', 'download']:
    os.makedirs(os.path.join(LOG_DIR, folder), exist_ok=True)

def setup_logger(name, log_file):
    """Configura un logger con archivo específico"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Evitar duplicados
    if logger.handlers:
        return logger
    
    # Handler para archivo
    file_handler = logging.FileHandler(
        os.path.join(LOG_DIR, log_file),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # Formato
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    # También imprimir en consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Loggers específicos
payment_logger = setup_logger('payment', 'payment/payment.log')
email_logger = setup_logger('email', 'email/email.log')
download_logger = setup_logger('download', 'download/download.log')
scan_logger = setup_logger('scan', 'scan.log')
webhook_logger = setup_logger('webhook', 'payment/webhook.log')