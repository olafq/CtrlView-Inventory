from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.db.models import Tenant


def get_current_tenant(
    request: Request,
    db: Session = Depends(get_db),
):
    host = request.headers.get("host")

    if not host:
        raise HTTPException(status_code=400, detail="Host header missing")

    # Ej: melo.ctrlview.com
    parts = host.split(".")

    if len(parts) < 3:
        # sin subdominio → default
        slug = "default"
    else:
        slug = parts[0]

    tenant = db.query(Tenant).filter(
        Tenant.slug == slug,
        Tenant.is_active == True
    ).first()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return tenant