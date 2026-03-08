from fastapi import Request, HTTPException, Depends, Header
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.db.models import Tenant


def get_current_tenant(
    request: Request,
    db: Session = Depends(get_db),
    x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
):
    # 1) ✅ Prioridad: header (ideal para Vercel / Postman / cronjobs)
    if x_tenant_slug:
        tenant = (
            db.query(Tenant)
            .filter(Tenant.slug == x_tenant_slug, Tenant.is_active == True)
            .first()
        )
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found (X-Tenant-Slug)")
        return tenant

    # 2) ✅ Fallback: host/subdomain (SaaS real)
    host = request.headers.get("host")
    if not host:
        raise HTTPException(status_code=400, detail="Host header missing")

    # host puede venir con puerto "melo.ctrlview.com:10000"
    host = host.split(":")[0]

    parts = host.split(".")
    # Ej: melo.ctrlview.com => slug=melo
    # Si es ctrlview.com o localhost => default
    slug = parts[0] if len(parts) >= 3 else "default"

    tenant = (
        db.query(Tenant)
        .filter(Tenant.slug == slug, Tenant.is_active == True)
        .first()
    )

    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant not found (slug={slug})")

    return tenant