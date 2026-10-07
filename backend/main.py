import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db_and_tables
from routers import transactions, portfolio, dashboard, settings, trading, market, data, analytics, screener

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(title="Financial OS Backend", lifespan=lifespan)

# CORS Seguro: configurable mediante variable de entorno o puertos locales de desarrollo
cors_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS", "")
if cors_origins_env:
    allowed_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:80",
        "http://127.0.0.1:80",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Conectar rutas
app.include_router(transactions.router)
app.include_router(portfolio.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(trading.router)
app.include_router(market.router)
app.include_router(data.router)
app.include_router(analytics.router)
app.include_router(screener.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, reload_dirs=["backend"])