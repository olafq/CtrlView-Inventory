import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# 1. Imports de Base de Datos y Sesión
from app.db.session import SessionLocal, engine, Base

# 2. Importación de Modelos (Para que SQLAlchemy los reconozca)
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.models.channel import Channel

# 3. Importación de Routers
from app.modules.auth.router import router as auth_router
from app.modules.channels.router import router as channels_router
from app.modules.imports.router import router as imports_router

# Routers de Integraciones (Consolidados)
from app.modules.integrations.mercadolibre.router_oauth import router as ml_oauth_router
from app.modules.integrations.mercadolibre.router import router as ml_router # <-- ESTE es el unificado
from app.modules.integrations.mercadolibre.router_orders import router as ml_orders_router
from app.api.Webhooks.mercadolibre import router as ml_webhook_router
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lógica de inicio y cierre.
    Mantenemos la inicialización de canales básicos para el primer Tenant.
    """
    db = SessionLocal()
    try:
        first_tenant = db.query(Tenant).first()
        if first_tenant:
            default_channels = [
                {"name": "MercadoLibre", "type": "mercadolibre"},
                {"name": "Web", "type": "web"},
                {"name": "POS", "type": "pos"}
            ]
            for ch in default_channels:
                exists = db.query(Channel).filter_by(
                    name=ch["name"], 
                    tenant_id=first_tenant.id
                ).first()
                if not exists:
                    new_channel = Channel(
                        name=ch["name"], 
                        type=ch["type"], 
                        tenant_id=first_tenant.id
                    )
                    db.add(new_channel)
            db.commit()
            print(f"✅ Canales inicializados para: {first_tenant.name}")
    except Exception as e:
        print(f"❌ Error en lifespan: {e}")
        db.rollback()
    finally:
        db.close()
    yield

app = FastAPI(
    title="IdentityOS Inventory Engine", # Nombre actualizado a tu proyecto
    version="1.1.0",
    lifespan=lifespan
)

# ==========================================
# 🛡️ Configuración de CORS
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ctrlview-inventory-ui.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "*" 
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health():
    return {
        "status": "online", 
        "service": "IdentityOS Backend",
        "engine": "FastAPI + SQLAlchemy"
    }

# ==========================================
# 🛣️ Registro de Routers
# ==========================================
app.include_router(auth_router) 
app.include_router(channels_router)
app.include_router(imports_router)

# Integración Mercado Libre
app.include_router(ml_oauth_router) # Maneja el login/vinculación
app.include_router(ml_router)       # Maneja Items e Importación (El que arreglamos hoy)
app.include_router(ml_orders_router) # Maneja ventas y pedidos
app.include_router(ml_webhook_router)