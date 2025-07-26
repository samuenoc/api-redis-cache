import os
import firebase_admin
from firebase_admin import credentials, auth
import requests
from fastapi import HTTPException
import logging
from dotenv import load_dotenv

# Configuración inicial
load_dotenv()
logger = logging.getLogger(__name__)

# Validar variables de entorno
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY")

if not FIREBASE_CREDENTIALS_PATH or not FIREBASE_WEB_API_KEY:
    raise ValueError("❌ Configuración de Firebase incompleta en .env")

# Reiniciar Firebase para evitar cache
if firebase_admin._apps:
    firebase_admin.delete_app(firebase_admin.get_app())

# Inicializar Firebase con credenciales
try:
    cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    firebase_app = firebase_admin.initialize_app(cred)
    logger.info("✅ Firebase Admin SDK inicializado correctamente")
except Exception as e:
    logger.error(f"❌ Error crítico al inicializar Firebase: {e}")
    raise

def create_firebase_user(email: str, password: str):
    """Crea un usuario en Firebase con validación de contraseña."""
    # Validación previa
    if not isinstance(password, str) or len(password) < 6:
        raise HTTPException(
            status_code=400,
            detail="La contraseña debe tener al menos 6 caracteres"
        )

    try:
        user = auth.create_user(email=email, password=password)
        logger.info(f"✅ Usuario creado: {email}")
        return user
    except auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    except ValueError as e:  # Captura errores de formato
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error crítico al crear usuario: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

def firebase_login(email: str, password: str) -> str:
    """Autentica al usuario y retorna un JWT único."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()  # Lanza error para códigos 4XX/5XX
        id_token = response.json()["idToken"]
        
        # Debug: Verifica que el token sea único
        logger.debug(f"Token generado para {email}: {id_token[:10]}...")
        return id_token

    except requests.exceptions.RequestException as e:
        error_msg = response.json().get("error", {}).get("message", "Error en autenticación")
        logger.error(f"❌ Error en login ({email}): {error_msg}")
        raise HTTPException(
            status_code=401 if "INVALID_" in error_msg else 500,
            detail=error_msg
        )

def verify_id_token(token: str):
    """Verifica el JWT usando la instancia de Firebase."""
    try:
        return auth.verify_id_token(token, app=firebase_app)  # Usa la app explícita
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
    except Exception as e:
        logger.error(f"❌ Error al verificar token: {e}")
        raise HTTPException(status_code=401, detail="Error de autenticación")