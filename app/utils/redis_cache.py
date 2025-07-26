# utils/redis_cache.py
import redis
import json
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import logging
from urllib.parse import urlparse

load_dotenv()

logger = logging.getLogger("redis-cache")

class RedisCache:
    def __init__(self):
        # Configuración de Azure Redis
        azure_redis_url = os.getenv("AZURE_REDIS_URL")
        
        if azure_redis_url:
            # Parsear la URL de conexión de Azure Redis
            parsed = urlparse(azure_redis_url)
            self.redis_host = parsed.hostname
            self.redis_port = parsed.port or 6380  # Azure Redis usa 6380 por defecto para SSL
            self.redis_password = parsed.password
            self.redis_db = 0  # Azure Redis solo soporta DB 0
            self.ssl = True  # Azure Redis requiere SSL
        else:
            # Configuración local para desarrollo (usar solo en desarrollo)
            self.redis_host = os.getenv("REDIS_HOST", "localhost")
            self.redis_port = int(os.getenv("REDIS_PORT", 6379))
            self.redis_password = os.getenv("REDIS_PASSWORD")
            self.redis_db = int(os.getenv("REDIS_DB", 0))
            self.ssl = False
        
        # Conectar a Redis
        try:
            self.client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                db=self.redis_db,
                ssl=self.ssl,
                ssl_cert_reqs=None,  # Para desarrollo, en producción usa certificados válidos
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.client.ping()
            logger.info(f"✅ Redis conectado: {self.redis_host}:{self.redis_port} (SSL: {self.ssl})")
        except redis.ConnectionError as e:
            logger.error(f"❌ Error conectando a Redis: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"❌ Error inesperado conectando a Redis: {e}")
            self.client = None
    
    def generate_cache_key(self, base_key: str, query_params: Dict[str, Any]) -> str:
        """
        Generar llave dinámica basada en query parameters
        Ejemplo: catalog:game_title=Portal&behavior_name=achievement
        """
        if not query_params:
            return f"{base_key}:all"
        
        # Filtrar parámetros None y ordenar para consistencia
        filtered_params = {k: v for k, v in query_params.items() if v is not None}
        
        if not filtered_params:
            return f"{base_key}:all"
        
        # Crear string de parámetros ordenados
        param_string = "&".join([f"{k}={v}" for k, v in sorted(filtered_params.items())])
        cache_key = f"{base_key}:{param_string}"
        
        logger.debug(f"🔑 Cache key generada: {cache_key}")
        return cache_key
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Obtener datos del caché"""
        if not self.client:
            logger.warning("❌ Redis no conectado - CACHE MISS")
            return None
        
        try:
            cached_data = self.client.get(key)
            if cached_data:
                logger.info(f"🎯 CACHE HIT: {key}")
                return json.loads(cached_data)
            else:
                logger.debug(f"❌ CACHE MISS: {key}")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error deserializando caché {key}: {e}")
            # Eliminar caché corrupto
            self.delete(key)
            return None
        except Exception as e:
            logger.error(f"❌ Error obteniendo caché {key}: {e}")
            return None
    
    def set(self, key: str, data: Dict[str, Any], ttl: int = 3600) -> bool:
        """Guardar datos en caché con TTL (Time To Live)"""
        if not self.client:
            logger.warning("❌ Redis no conectado - No se puede guardar caché")
            return False
        
        try:
            serialized_data = json.dumps(data, default=str)
            result = self.client.setex(key, ttl, serialized_data)
            logger.info(f"💾 CACHE SET: {key} (TTL: {ttl}s)")
            return result
        except Exception as e:
            logger.error(f"❌ Error guardando caché {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Eliminar una llave específica"""
        if not self.client:
            return False
        
        try:
            result = self.client.delete(key)
            if result > 0:
                logger.info(f"🗑️ CACHE DELETE: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"❌ Error eliminando caché {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Eliminar múltiples llaves que coincidan con un patrón"""
        if not self.client:
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"🗑️ CACHE DELETE PATTERN: {pattern} - {deleted} keys deleted")
                return deleted
            else:
                logger.debug(f"🗑️ No keys found for pattern: {pattern}")
            return 0
        except Exception as e:
            logger.error(f"❌ Error eliminando patrón {pattern}: {e}")
            return 0
    
    def invalidate_catalog_cache(self, game_title: str = None, behavior_name: str = None, user_id: int = None) -> int:
        """
        Invalidación inteligente del caché del catálogo
        """
        patterns_to_delete = []
        
        # Si se especifica game_title, invalidar todas las consultas que lo incluyan
        if game_title:
            patterns_to_delete.append(f"catalog:*game_title={game_title}*")
        
        # Si se especifica behavior_name, invalidar todas las consultas que lo incluyan
        if behavior_name:
            patterns_to_delete.append(f"catalog:*behavior_name={behavior_name}*")
        
        # Si se especifica user_id, invalidar todas las consultas que lo incluyan
        if user_id:
            patterns_to_delete.append(f"catalog:*user_id={user_id}*")
        
        # También invalidar el caché de "todos los resultados"
        patterns_to_delete.append("catalog:all")
        
        total_deleted = 0
        for pattern in patterns_to_delete:
            deleted = self.delete_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"🔄 Invalidación de caché completada: {total_deleted} keys eliminadas")
        return total_deleted
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del caché"""
        if not self.client:
            return {
                "status": "disconnected",
                "error": "Redis client not initialized"
            }
        
        try:
            info = self.client.info()
            catalog_keys = len(self.client.keys("catalog:*"))
            
            return {
                "status": "connected",
                "total_keys": info.get("db0", {}).get("keys", 0),
                "catalog_keys": catalog_keys,
                "memory_used": info.get("used_memory_human", "0"),
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "config": {
                    "host": self.redis_host,
                    "port": self.redis_port,
                    "db": self.redis_db
                }
            }
        except Exception as e:
            logger.error(f"❌ Error obteniendo stats: {e}")
            return {
                "status": "error", 
                "error": str(e),
                "config": {
                    "host": self.redis_host,
                    "port": self.redis_port,
                    "db": self.redis_db
                }
            }
    
    def flush_all(self) -> bool:
        """Limpiar todo el caché (usar con cuidado)"""
        if not self.client:
            return False
        
        try:
            result = self.client.flushdb()
            logger.warning("🗑️ CACHE FLUSH ALL - Todo el caché eliminado")
            return result
        except Exception as e:
            logger.error(f"❌ Error limpiando todo el caché: {e}")
            return False
        

# Instancia global del caché
def invalidate_catalog_cache_by_category(self, category: str) -> int:
    """
    Invalidación específica por categoría para el endpoint /catalog
    """
    # Eliminar la clave exacta para esta categoría
    exact_key = f"catalog:category={category}"
    deleted = self.delete(exact_key)
    
    # También eliminar cualquier clave que incluya esta categoría en combinación
    pattern = f"catalog:*category={category}*"
    deleted += self.delete_pattern(pattern)
    
    # Eliminar el caché de "todos los resultados"
    deleted += self.delete("catalog:all")
    
    logger.info(f"🔄 Invalidación de caché para categoría '{category}': {deleted} keys eliminadas")
    return deleted
cache = RedisCache()

def is_connected(self) -> bool:
    """Verifica si la conexión a Redis está activa"""
    if not self.client:
        return False
    try:
        return self.client.ping()
    except:
        return False


