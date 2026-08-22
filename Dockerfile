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

EXPOSE 8080

# Producción: seo_server registra SEO, scanner y rutas de idioma.
CMD ["sh", "-c", "gunicorn seo_server:app --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:${PORT:-8080}"]
