from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from contextlib import asynccontextmanager
import subprocess

from app.db.session import SessionLocal
from app.db.models.channel import Channel

from app.modules.channels.router import router as channels_router
from app.modules.imports.router import router as imports_router
from app.modules.integrations.mercadolibre.router_oauth import router as ml_oauth_router
from app.modules.integrations.mercadolibre.router_api import router as ml_api_router
from app.modules.integrations.mercadolibre.router_orders import router as ml_orders_router
from app.modules.integrations.mercadolibre.router_import import (
    router as ml_import_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # =========================
    # 1️⃣ Run Alembic migrations
    # =========================
    try:
        subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
        )
        print("✅ Alembic migrations applied")
    except Exception as e:
        print("❌ Alembic migration failed:", e)
        raise

    # =========================
    # 2️⃣ Seed mínimo de channels
    # =========================
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

    yield  # 🚀 la app corre


app = FastAPI(
    title="Inventory Sync Engine",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def health():
    return {"status": "ok"}


# =========================
# Routers
# =========================
app.include_router(channels_router)
app.include_router(imports_router)
app.include_router(ml_oauth_router)
app.include_router(ml_api_router)
app.include_router(ml_orders_router)
app.include_router(ml_import_router)
