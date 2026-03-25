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
    # Lógica al iniciar la aplicación
    db = SessionLocal()
    try:
        # 1. Buscamos si existe algún Tenant (Empresa)
        first_tenant = db.query(Tenant).first()
        
        if first_tenant:
            # 2. Definimos los canales básicos
            default_channels = [
                {"name": "MercadoLibre", "type": "mercadolibre"},
                {"name": "Web", "type": "web"},
                {"name": "POS", "type": "pos"}
            ]
            
            for ch in default_channels:
                # 3. Verificamos si el canal ya existe para ESTE tenant
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
            print("⚠️ No hay Tenants en la base de datos. Los canales se crearán cuando se registre la primera empresa.")
            
    except Exception as e:
        print(f"❌ Error en lifespan: {e}")
        db.rollback()
    finally:
        db.close()
        
    yield
    # Lógica al cerrar la aplicación (si es necesaria)


app = FastAPI(
    title="Sync App - Inventory Engine",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=True  # Agregá esto para evitar redirecciones que rompan CORS
)

# ==========================================
# 🛡️ Configuración de CORS
# ==========================================


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # El asterisco permite CUALQUIER origen (Vercel, Local, etc.)
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