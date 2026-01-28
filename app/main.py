from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from app.core.config import is_dev
from app.db.dependencies import get_db
from app.db.models import Channel

from app.modules.channels.router import router as channels_router
from app.modules.imports.router import router as imports_router
from app.modules.integrations.mercadolibre.router_oauth import router as ml_oauth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 🔹 STARTUP
    db: Session = next(get_db())

    defaults = [
        ("MercadoLibre", "mercadolibre"),
        ("Web", "web"),
        ("POS", "pos"),
    ]

    existing = {c.type for c in db.query(Channel).all()}

    for name, ctype in defaults:
        if ctype not in existing:
            db.add(Channel(name=name, type=ctype))

    db.commit()

    yield  # 👉 la app corre

    # 🔹 SHUTDOWN (opcional)
    db.close()


app = FastAPI(
    title="Inventory Sync Engine",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/dev/bootstrap")
def bootstrap(db: Session = Depends(get_db)):
    if not is_dev():
        raise HTTPException(status_code=403, detail="Not allowed")

    existing = {c.name for c in db.query(Channel).all()}
    for name, ctype in [
        ("MercadoLibre", "mercadolibre"),
        ("Web", "web"),
        ("POS", "pos"),
    ]:
        if name not in existing:
            db.add(Channel(name=name, type=ctype))

    db.commit()
    return {"ok": True}


app.include_router(channels_router)
app.include_router(imports_router)
app.include_router(ml_oauth_router)
