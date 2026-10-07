#!/usr/bin/env bash
# Script para iniciar Financial OS (Backend FastAPI + Frontend Vite)

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=========================================="
echo "🚀 Iniciando Financial OS"
echo "=========================================="

# 1. Verificar entorno virtual de Python
if [ -d "$DIR/.venv" ]; then
    PYTHON_EXEC="$DIR/.venv/bin/python"
    UVICORN_EXEC="$DIR/.venv/bin/uvicorn"
elif [ -d "$DIR/backend/.venv" ]; then
    PYTHON_EXEC="$DIR/backend/.venv/bin/python"
    UVICORN_EXEC="$DIR/backend/.venv/bin/uvicorn"
else
    PYTHON_EXEC="python3"
    UVICORN_EXEC="uvicorn"
fi

# Función de limpieza al detener con Ctrl+C
cleanup() {
    echo ""
    echo "🛑 Deteniendo Financial OS..."
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    exit 0
}

trap cleanup INT TERM

# 2. Iniciar Backend (FastAPI en puerto 8000)
echo "📦 Iniciando Backend en http://127.0.0.1:8000 ..."
cd "$DIR/backend"
"$UVICORN_EXEC" main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!
cd "$DIR"

# 3. Iniciar Frontend (Vite en puerto 5173)
echo "💻 Iniciando Frontend en http://localhost:5173 ..."
cd "$DIR/frontend"
npm run dev &
FRONTEND_PID=$!
cd "$DIR"

echo ""
echo "✅ Aplicación en ejecución:"
echo "   - Frontend: http://localhost:5173"
echo "   - Backend API: http://127.0.0.1:8000"
echo "   - Documentación Swagger: http://127.0.0.1:8000/docs"
echo "Presiona Ctrl+C para detener ambos servicios."
echo "=========================================="

# Esperar a que los procesos finalicen
wait
