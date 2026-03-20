import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.tenant import Tenant
from app.core.security import get_password_hash, verify_password, create_access_token
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter(prefix="/auth", tags=["Autenticación"])

# Esquema para el registro
class RegisterSchema(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    is_admin: bool  # True = Empresa, False = Empleado
    company_name: Optional[str] = None # Solo para Empresa
    company_code: Optional[str] = None # Solo para Empleado

@router.post("/register")
def register(data: RegisterSchema, db: Session = Depends(get_db)):
    # 1. Verificar si el usuario ya existe
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado.")

    if data.is_admin:
        # --- FLUJO EMPRESA ---
        if not data.company_name:
            raise HTTPException(status_code=400, detail="Nombre de empresa requerido.")
        
        # Crear el Tenant (la Empresa)
        new_tenant = Tenant(
            name=data.company_name,
            slug=data.company_name.lower().replace(" ", "-") + "-" + str(uuid.uuid4())[:4],
            company_code=str(uuid.uuid4())[:8].upper() # Genera el código para invitar empleados
        )
        db.add(new_tenant)
        db.flush() # Para obtener el ID antes del commit
        tenant_id = new_tenant.id
        role = "admin"
        response_code = new_tenant.company_code
    else:
        # --- FLUJO EMPLEADO ---
        if not data.company_code:
            raise HTTPException(status_code=400, detail="Código de empresa requerido.")
        
        # Buscar la empresa por el código
        tenant = db.query(Tenant).filter(Tenant.company_code == data.company_code).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Código de empresa no válido.")
        
        tenant_id = tenant.id
        role = "employee"
        response_code = data.company_code

    # 2. Crear el Usuario vinculado al Tenant
    new_user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        role=role,
        tenant_id=tenant_id
    )
    db.add(new_user)
    db.commit()

    return {
        "status": "success", 
        "message": "Usuario creado correctamente",
        "company_code": response_code # Se lo mostramos para que lo comparta con su equipo
    }