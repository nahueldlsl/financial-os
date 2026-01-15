# backend/Dockerfile

# 1. Usar una imagen base de Python ligera
FROM python:3.10-slim

# 2. Crear carpeta de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiar el archivo de requisitos e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar todo el código del backend al contenedor
COPY . .

# 5. Comando para encender el servidor (Host 0.0.0.0 es vital en Docker)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]