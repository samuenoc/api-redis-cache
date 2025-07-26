import os
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException
from typing import Dict, Any
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Configuración JWT
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 30))
import os
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException
from typing import Dict, Any
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Configuración JWT
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 30))

if not JWT_SECRET:
    raise ValueError("❌ JWT_SECRET no configurado en .env")

def create_admin_jwt(firebase_uid: str, email: str, user_id: int) -> str:
    """
    Crea un JWT personalizado solo para usuarios administradores.
    Este token contendrá información adicional sobre los privilegios.
    """
    payload = {
        "sub": firebase_uid,
        "email": email,
        "user_id": user_id,
        "is_admin": True,  # Siempre True porque solo llamamos esta función para admins
        "iss": "custom-admin-jwt",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    }
    
    try:
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        logger.debug(f"✅ JWT de admin creado para {email}")
        return token
    except Exception as e:
        logger.error(f"❌ Error creando JWT: {e}")
        raise HTTPException(status_code=500, detail="Error generando token")

def verify_custom_jwt(token: str) -> Dict[str, Any]:
    """
    Verifica un JWT personalizado y devuelve su payload.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("iss") != "custom-admin-jwt":
            raise HTTPException(status_code=401, detail="Token inválido")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
    except Exception as e:
        logger.error(f"❌ Error verificando JWT: {e}")
        raise HTTPException(status_code=401, detail="Error verificando token")
if not JWT_SECRET:
    raise ValueError("❌ JWT_SECRET no configurado en .env")

def create_admin_jwt(firebase_uid: str, email: str, user_id: int) -> str:
    """
    Crea un JWT personalizado solo para usuarios administradores.
    Este token contendrá información adicional sobre los privilegios.
    """
    payload = {
        "sub": firebase_uid,
        "email": email,
        "user_id": user_id,
        "is_admin": True,  # Siempre True porque solo llamamos esta función para admins
        "iss": "custom-admin-jwt",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    }
    
    try:
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        logger.debug(f"✅ JWT de admin creado para {email}")
        return token
    except Exception as e:
        logger.error(f"❌ Error creando JWT: {e}")
        raise HTTPException(status_code=500, detail="Error generando token")

def verify_custom_jwt(token: str) -> Dict[str, Any]:
    """
    Verifica un JWT personalizado y devuelve su payload.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("iss") != "custom-admin-jwt":
            raise HTTPException(status_code=401, detail="Token inválido")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
    except Exception as e:
        logger.error(f"❌ Error verificando JWT: {e}")
        raise HTTPException(status_code=401, detail="Error verificando token")