import os
import subprocess
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# 1. Imports de Base de Datos y Sesión
from app.db.session import SessionLocal, engine, Base

# 2. Importación de Modelos (Necesarios para que create_all los detecte)
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.models.channel import Channel

# 3. Importación de Routers
from app.modules.auth.router import router as auth_router
from app.modules.channels.router import router as channels_router
from app.modules.imports.router import router as imports_router
from app.modules.integrations.mercadolibre.router_oauth import router as ml_oauth_router
from app.modules.integrations.mercadolibre.router_api import router as ml_api_router
from app.modules.integrations.mercadolibre.router_orders import router as ml_orders_router
from app.modules.integrations.mercadolibre.router_import import router as ml_import_router

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ==========================================
    # 🛠️ 1. Crear tablas si no existen
    # ==========================================
    # Esto asegura que User y Tenant existan en la DB antes de registrar
    Base.metadata.create_all(bind=engine)

    # ==========================================
    # 🌱 2. Seed de Canales por defecto
    # ==========================================
    db = SessionLocal()
    try:
        defaults = [
            ("MercadoLibre", "mercadolibre"),
            ("Web", "web"),
            ("POS", "pos"),
        ]

        existing_types = {c.type for c in db.query(Channel).all()}

        for name, ctype in defaults:
            if ctype not in existing_types:
                db.add(Channel(name=name, type=ctype))

        db.commit()
    finally:
        db.close()

    yield  # 🚀 La aplicación empieza a recibir peticiones


app = FastAPI(
    title="Sync App - Inventory Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# ==========================================
# 🛡️ Configuración de CORS
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ctrlview-inventory-ui.vercel.app",
        "https://oauth.goqconsultant.com",
        "http://localhost:3000", # Agrego localhost por si testeas el Front local
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health():
    return {"status": "ok", "service": "Sync App Backend"}


# ==========================================
# 🛣️ Registro de Routers
# ==========================================
# El router de AUTH debe estar presente para Empresa/Empleado
app.include_router(auth_router) 
app.include_router(channels_router)
app.include_router(imports_router)
app.include_router(ml_oauth_router)
app.include_router(ml_api_router)
app.include_router(ml_orders_router)
app.include_router(ml_import_router)