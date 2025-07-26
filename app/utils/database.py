# utils/database.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import logging
from typing import Optional

load_dotenv()

logger = logging.getLogger(__name__)

def get_db_connection() -> Optional[psycopg2.extensions.connection]:
    """
    Crear conexión a PostgreSQL Azure
    """
    try:
        connection = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            cursor_factory=RealDictCursor,
            sslmode='require'  # Importante para Azure PostgreSQL
        )
        logger.debug("✅ Conexión a base de datos establecida")
        return connection
    except Exception as e:
        logger.error(f"❌ Error conectando a la base de datos: {e}")
        return None

def test_db_connection() -> bool:
    """
    Probar la conexión a la base de datos
    """
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            logger.info("✅ Test de conexión a DB exitoso")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Error en test de conexión: {e}")
        return False

def get_db_config() -> dict:
    """
    Obtener configuración de la base de datos (para debugging)
    """
    return {
        "host": os.getenv('DB_HOST', 'Not configured'),
        "port": os.getenv('DB_PORT', '5432'),
        "database": os.getenv('DB_NAME', 'Not configured'),
        "user": os.getenv('DB_USER', 'Not configured'),
        "password": "***" if os.getenv('DB_PASSWORD') else 'Not configured'
    }