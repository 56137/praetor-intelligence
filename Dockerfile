# 1. Imagen Base Ligera: Reduce la superficie de ataque y el tiempo de despliegue
FROM python:3.11-slim

# 2. Variables de Entorno: Evita la creación de archivos .pyc y asegura logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3. Directorio de Trabajo
WORKDIR /app

# 4. Aislamiento de Seguridad: Creación del usuario y grupo non-root
RUN addgroup --system praetorgroup && adduser --system --group praetoruser

# 5. Caché de Dependencias: Copiar solo requirements primero para optimizar los tiempos de build (CI/CD)
COPY requirements.txt .

# 6. Instalación de Dependencias
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copiar el Código Fuente de la Misión
COPY . .

# 8. Permisos: Transferir la propiedad de los archivos al usuario sin privilegios
RUN chown -R praetoruser:praetorgroup /app

# 9. Cambio de Contexto: Activar el usuario non-root (Punto crítico de seguridad)
USER praetoruser

# 10. Exponer el puerto estándar de Cloud Run
EXPOSE 8080

# 11. Ejecución: Comando de arranque con Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
