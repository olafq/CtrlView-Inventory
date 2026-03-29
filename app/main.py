import os
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
    """
    Lógica de inicio y cierre de la aplicación.
    Inicializa canales básicos si existe un Tenant.
    """
    db = SessionLocal()
    try:
        # Buscamos si existe algún Tenant (Empresa)
        first_tenant = db.query(Tenant).first()
        
        if first_tenant:
            # Definimos los canales básicos
            default_channels = [
                {"name": "MercadoLibre", "type": "mercadolibre"},
                {"name": "Web", "type": "web"},
                {"name": "POS", "type": "pos"}
            ]
            
            for ch in default_channels:
                # Verificamos si el canal ya existe para este tenant
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
            print(f"✅ Canales inicializados para el Tenant: {first_tenant.name}")
        else:
            print("⚠️ No hay Tenants en la base de datos. Los canales se crearán al registrar la primera empresa.")
            
    except Exception as e:
        print(f"❌ Error en lifespan: {e}")
        db.rollback()
    finally:
        db.close()
    yield

# Configuración de la instancia de FastAPI
app = FastAPI(
    title="CtrlView Inventory Engine",
    version="1.0.0",
    lifespan=lifespan
)

# ==========================================
# 🛡️ Configuración de CORS
# ==========================================
# Agregamos tus dominios específicos además del "*" para mayor compatibilidad con navegadores
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
        "status": "ok", 
        "service": "CtrlView Backend",
        "version": "1.0.0"
    }

# ==========================================
# 🛣️ Registro de Routers
# ==========================================
app.include_router(auth_router) 
app.include_router(channels_router)
app.include_router(imports_router)
app.include_router(ml_oauth_router)
app.include_router(ml_api_router)
app.include_router(ml_orders_router)
app.include_router(ml_import_router)