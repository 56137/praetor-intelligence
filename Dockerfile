# Imagen base ligera y compatible con Flask/Gunicorn
FROM python:3.11-slim

# Logs en tiempo real y sin archivos .pyc
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Usuario sin privilegios para ejecutar PRAETOR
RUN addgroup --system praetorgroup && adduser --system --group praetoruser

# Instalar dependencias antes de copiar el código para aprovechar la caché
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicación
COPY . .

# Permisos para el usuario no-root
RUN chown -R praetoruser:praetorgroup /app
USER praetoruser

# Cloud Run proporciona PORT; 8080 es el valor habitual
EXPOSE 8080

# PRAETOR es Flask: app.py expone app
CMD ["sh", "-c", "gunicorn app:app --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:${PORT:-8080}"]
