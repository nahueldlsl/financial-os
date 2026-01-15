# frontend/Dockerfile

# 1. Usar imagen de Node.js ligera
FROM node:22-alpine

# 2. Carpeta de trabajo
WORKDIR /app

# 3. Copiar dependencias e instalarlas
COPY package*.json ./
RUN npm install

# 4. Copiar el código fuente
COPY . .

# 5. Exponer el puerto de Vite
EXPOSE 5173

# 6. Encender modo desarrollo (Agregamos --host para que Docker lo vea)
CMD ["npm", "run", "dev", "--", "--host"]