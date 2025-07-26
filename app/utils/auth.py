# utils/auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import logging

from utils.database import get_db_connection
from utils.firebase import verify_id_token

logger = logging.getLogger(__name__)

# Configurar esquema de seguridad Bearer
security = HTTPBearer(auto_error=False)

def verify_firebase_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    """
    Verificar token de Firebase y retornar datos del token
    """
    if not credentials:
        logger.warning("❌ Token de autorización no proporcionado")
        raise HTTPException(
            status_code=401, 
            detail="Token de autorización requerido"
        )
    
    try:
        token_data = verify_id_token(credentials.credentials)
        logger.debug(f"✅ Token verificado para UID: {token_data.get('uid')}")
        return token_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error verificando token: {e}")
        raise HTTPException(
            status_code=401, 
            detail="Token inválido"
        )

def get_current_user(token_data: Dict[str, Any] = Depends(verify_firebase_token)) -> Dict[str, Any]:
    """
    Obtener usuario actual desde la base de datos usando el token de Firebase
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(
                status_code=500, 
                detail="Error de conexión a la base de datos"
            )
        
        cur = conn.cursor()
        cur.execute("""
            SELECT id, firebase_uid, email, is_active, is_admin, created_at
            FROM users
            WHERE firebase_uid = %s AND is_active = true
        """, (token_data.get("uid"),))
        
        user = cur.fetchone()
        cur.close()
        
        if not user:
            logger.warning(f"❌ Usuario no encontrado o inactivo: {token_data.get('uid')}")
            raise HTTPException(
                status_code=404, 
                detail="Usuario no encontrado o inactivo"
            )
        
        user_data = dict(user)
        logger.debug(f"✅ Usuario obtenido: {user_data['email']}")
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo usuario: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno del servidor"
        )
    finally:
        if conn:
            conn.close()

def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Verificar que el usuario actual tenga permisos de administrador
    """
    if not current_user.get("is_admin"):
        logger.warning(f"❌ Acceso denegado - Usuario no admin: {current_user.get('email')}")
        raise HTTPException(
            status_code=403, 
            detail="Se requieren permisos de administrador"
        )
    
    logger.debug(f"✅ Acceso admin concedido a: {current_user.get('email')}")
    return current_user

def require_active_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Verificar que el usuario esté activo (útil para endpoints que requieren usuario activo)
    """
    if not current_user.get("is_active"):
        logger.warning(f"❌ Usuario inactivo intentó acceder: {current_user.get('email')}")
        raise HTTPException(
            status_code=403, 
            detail="Usuario inactivo"
        )
    
    return current_user  

from utils.jwt import verify_custom_jwt

def verify_custom_admin_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Verifica el JWT personalizado de admin.
    """
    if not credentials:
        logger.warning("❌ Token de autorización no proporcionado")
        raise HTTPException(
            status_code=401, 
            detail="Token de autorización requerido"
        )
    
    try:
        token_data = verify_custom_jwt(credentials.credentials)
        if not token_data.get("is_admin"):
            raise HTTPException(status_code=403, detail="Se requieren privilegios de admin")
        
        logger.debug(f"✅ JWT de admin verificado para: {token_data.get('email')}")
        return token_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error verificando token admin: {e}")
        raise HTTPException(
            status_code=401, 
            detail="Token admin inválido"
        )