from fastapi import APIRouter, HTTPException
from models.auth import UserSignup, UserLogin, SignupResponse, LoginResponse
from utils.firebase import create_firebase_user, firebase_login
from utils.database import get_db_connection
from utils.telemetry import telemetry_service
import logging
from firebase_admin import auth  # Importamos auth para obtener el UID del token

logger = logging.getLogger("auth_controller")
router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/signup", response_model=SignupResponse)
async def signup(user_data: UserSignup):
    """Registrar nuevo usuario"""
    telemetry_service.log_and_trace_request("signup")
    
    try:
        firebase_user = create_firebase_user(user_data.email, user_data.password)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (firebase_uid, email, is_active, is_admin)
            VALUES (%s, %s, %s, %s)
            RETURNING id, firebase_uid, email, is_active, is_admin, created_at
        """, (firebase_user.uid, user_data.email, True, False))
        new_user = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Usuario creado: {user_data.email}")
        return {
            "message": "Usuario creado exitosamente",
            "user": dict(new_user),
        }
    except Exception as e:
        logger.error(f"Error en /signup: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=LoginResponse)
async def login(credentials: UserLogin):
    try:
        # 1. Autenticar en Firebase
        id_token = firebase_login(credentials.email, credentials.password)
        decoded_token = auth.verify_id_token(id_token)
        firebase_uid = decoded_token['uid']
        
        # 2. Obtener información del usuario de tu base de datos
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, email, is_admin FROM users 
            WHERE firebase_uid = %s AND is_active = true
        """, (firebase_uid,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        user_data = dict(user)
        
        # 3. Si es admin, generar JWT personalizado
        custom_jwt = None
        if user_data.get("is_admin"):
            from utils.jwt import create_admin_jwt
            custom_jwt = create_admin_jwt(
                firebase_uid=firebase_uid,
                email=user_data["email"],
                user_id=user_data["id"]
            )
        
        return {
            "message": "Login exitoso",
            "id_token": id_token,  # Token estándar de Firebase
            "firebase_uid": firebase_uid,
            "custom_jwt": custom_jwt,  # Solo presente si es admin
            "is_admin": user_data.get("is_admin", False),
            "instructions": {
                "standard_usage": "Usa el id_token en el header: Authorization: Bearer <id_token>",
                "admin_usage": "Para endpoints admin, usa el custom_jwt si está disponible"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))