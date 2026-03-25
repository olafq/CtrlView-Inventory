import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# Imports de tu proyecto
from app.db.session import get_db
from app.db.models.user import User

# Configuración básica - Asegúrate de que coincida con tu .env
SECRET_KEY = os.getenv("SECRET_KEY", "TU_CLAVE_SUPER_SECRETA_CORREGIDA")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 día

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esto permite que FastAPI extraiga el token del header "Authorization: Bearer <token>"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# --- Funciones de Contraseña ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    if not password:
        raise ValueError("Password cannot be empty")
    return pwd_context.hash(password)

# --- Funciones de Token ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- Dependencia para proteger rutas ---

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Valida el JWT y devuelve el objeto User completo desde la DB.
    Si el token es inválido o el usuario no existe, lanza una 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token de acceso",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificamos el token usando tu SECRET_KEY
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        if email is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
        
    # Buscamos al usuario en la base de datos
    user = db.query(User).filter(User.email == email).first()
    
    if user is None:
        raise credentials_exception
        
    return user