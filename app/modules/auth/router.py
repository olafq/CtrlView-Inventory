import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional

# Imports de lógica interna
from app.db.session import get_db
from app.db.models.channel import Channel
from app.db.models.user import User
from app.db.models.tenant import Tenant
from app.core.security import (
    get_password_hash, 
    verify_password, 
    create_access_token,
    get_current_user
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])

# --- ESQUEMAS ---

class LoginSchema(BaseModel):
    email: EmailStr
    password: str
    model_config = ConfigDict(extra="ignore")

class RegisterSchema(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    is_admin: bool = False
    company_name: Optional[str] = None
    company_code: Optional[str] = None
    model_config = ConfigDict(extra="ignore")

# --- ENDPOINTS ---

@router.get("/me")
def get_me(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Recupera el perfil del usuario, su tenant y sus canales de venta de forma dinámica.
    """
    # 1. Buscamos el tenant vinculado al usuario
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    
    # 2. BUSQUEDA DINÁMICA DE CANALES
    # Filtramos por el tenant_id del usuario logueado para que cada uno vea solo lo suyo
    channels = db.query(Channel).filter(Channel.tenant_id == current_user.tenant_id).all()
    
    # 3. Construimos la respuesta con TODA la información de identidad
    return {
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "tenant_id": current_user.tenant_id,  # Clave para el multi-tenancy
        "company_code": tenant.company_code if tenant else "No disponible",
        "company_name": tenant.name if tenant else "Sin Empresa",
        # Mapeamos los canales para que el Frontend sepa qué IDs usar (ej: 17 o 20)
        "channels": [
            {
                "id": c.id, 
                "name": c.name, 
                "type": c.type
            } for c in channels
        ]
    }

@router.post("/login")
@router.post("/login/", include_in_schema=False)
def login(data: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Credenciales incorrectas"
        )

    access_token = create_access_token(
        data={
            "sub": user.email, 
            "role": user.role, 
            "tenant_id": user.tenant_id,
            "full_name": user.full_name
        }
    )

    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    }

@router.post("/register")
def register(data: RegisterSchema, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado.")

    tenant_id = None
    role = "employee"
    response_code = ""

    if data.is_admin:
        if not data.company_name or not data.company_name.strip():
            raise HTTPException(status_code=400, detail="Nombre de empresa obligatorio.")
        
        clean_name = data.company_name.strip()
        unique_slug = f"{clean_name.lower().replace(' ', '-')}-{str(uuid.uuid4())[:4]}"
        unique_code = str(uuid.uuid4())[:8].upper()

        new_tenant = Tenant(name=clean_name, slug=unique_slug, company_code=unique_code)
        
        try:
            db.add(new_tenant)
            db.flush()
            tenant_id = new_tenant.id
            
            from app.db.models.channel import Channel
            db.add_all([
                Channel(name="Web", type="web", tenant_id=tenant_id),
                Channel(name="MercadoLibre", type="mercadolibre", tenant_id=tenant_id),
                Channel(name="POS", type="pos", tenant_id=tenant_id)
            ])

            role = "admin"
            response_code = new_tenant.company_code
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error en Tenant: {str(e)}")
    else:
        tenant = db.query(Tenant).filter(Tenant.company_code == data.company_code.strip().upper()).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Código inválido.")
        tenant_id = tenant.id
        role = "employee"
        response_code = tenant.company_code

    try:
        hash_final = get_password_hash(data.password)
        new_user = User(
            email=data.email,
            hashed_password=hash_final,
            full_name=data.full_name,
            role=role,
            tenant_id=tenant_id
        )
        db.add(new_user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error en User: {str(e)}")

    return {"status": "success", "company_code": response_code}