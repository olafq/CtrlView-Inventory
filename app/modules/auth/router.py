import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

# Imports internos
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.tenant import Tenant
from app.core.security import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Autenticación"])

# --- ESQUEMAS DE VALIDACIÓN ---

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

class RegisterSchema(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    is_admin: bool = False
    company_name: Optional[str] = None
    company_code: Optional[str] = None

# --- ENDPOINTS ---

@router.post("/register")
def register(data: RegisterSchema, db: Session = Depends(get_db)):
    # 1. Verificar si el usuario ya existe
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado.")

    tenant_id = None
    role = "employee"
    response_code = ""

    if data.is_admin:
        # --- FLUJO EMPRESA (ADMIN) ---
        if not data.company_name or not data.company_name.strip():
            raise HTTPException(status_code=400, detail="El nombre de la empresa es obligatorio para administradores.")
        
        clean_name = data.company_name.strip()
        unique_slug = f"{clean_name.lower().replace(' ', '-')}-{str(uuid.uuid4())[:4]}"
        unique_code = str(uuid.uuid4())[:8].upper()

        new_tenant = Tenant(
            name=clean_name,
            slug=unique_slug,
            company_code=unique_code
        )
        
        try:
            db.add(new_tenant)
            db.flush()  
            tenant_id = new_tenant.id
            
            # Semilla de canales iniciales
            from app.db.models.channel import Channel
            default_channels = [
                Channel(name="Web", type="web", tenant_id=tenant_id),
                Channel(name="MercadoLibre", type="mercadolibre", tenant_id=tenant_id),
                Channel(name="POS", type="pos", tenant_id=tenant_id)
            ]
            db.add_all(default_channels)

            role = "admin"
            response_code = new_tenant.company_code
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error al crear la empresa: {str(e)}")
    else:
        # --- FLUJO EMPLEADO ---
        if not data.company_code:
            raise HTTPException(status_code=400, detail="Código de empresa requerido para empleados.")
        
        tenant = db.query(Tenant).filter(Tenant.company_code == data.company_code.strip().upper()).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="El código de empresa no es válido.")
        
        tenant_id = tenant.id
        role = "employee"
        response_code = tenant.company_code

    # 2. Crear el Usuario (CORRECCIÓN: Limpieza de password antes de hashear)
    try:
        password_plana = str(data.password).strip()
        password_hasheada = get_password_hash(password_plana) # Hasheamos una sola vez

        new_user = User(
            email=data.email,
            hashed_password=password_hasheada, # Usamos el hash ya generado
            full_name=data.full_name,
            role=role,
            tenant_id=tenant_id
        )
        db.add(new_user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear el perfil de usuario: {str(e)}")

    return {
        "status": "success", 
        "message": "Registro completado exitosamente",
        "company_code": response_code
    }

@router.post("/login")
@router.post("/login/", include_in_schema=False)
def login(data: LoginSchema, db: Session = Depends(get_db)):
    # 1. Buscar al usuario por email
    user = db.query(User).filter(User.email == data.email).first()
    
    # 2. Validar existencia y contraseña
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="El email no está registrado."
        )
    
    # IMPORTANTE: verify_password toma (plana, hasheada)
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Contraseña incorrecta."
        )

    # 3. Crear el Token de acceso (JWT)
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