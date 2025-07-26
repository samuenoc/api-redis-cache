from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from utils.redis_cache import cache
from utils.telemetry import telemetry_service
import logging

logger = logging.getLogger("cache_controller")
router = APIRouter(prefix="/cache", tags=["Caché"])

@router.get("/stats")
async def get_cache_stats():
    """Obtener estadísticas del caché Redis"""
    telemetry_service.log_and_trace_request("cache_stats")
    
    with telemetry_service.tracer.start_as_current_span("cache.stats") as span:
        try:
            stats = cache.get_cache_stats()
            
            span.set_attributes({
                "cache.status": stats.get("status", "unknown"),
                "cache.total_keys": stats.get("total_keys", 0),
                "cache.catalog_keys": stats.get("catalog_keys", 0)
            })
            
            logger.info(f"✅ Cache stats retrieved: {stats}")
            return {
                "message": "Estadísticas del caché obtenidas",
                "stats": stats,
                "endpoints": {
                    "clear_cache": "/cache/clear",
                    "health": "/health"
                }
            }
            
        except Exception as e:
            span.set_attribute("error", str(e))
            logger.error(f"❌ Error obteniendo stats del caché: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear")
async def clear_cache(
    pattern: Optional[str] = Query("catalog:*", description="Patrón para limpiar caché")
):
    """Limpiar caché manualmente"""
    telemetry_service.log_and_trace_request("clear_cache", pattern=pattern)
    
    with telemetry_service.tracer.start_as_current_span("cache.clear") as span:
        try:
            deleted_keys = cache.delete_pattern(pattern)
            
            span.set_attributes({
                "cache.pattern": pattern,
                "cache.deleted_keys": deleted_keys
            })
            
            logger.info(f"✅ Cache cleared: {deleted_keys} keys deleted with pattern {pattern}")
            
            return {
                "message": f"Caché limpiado exitosamente",
                "pattern": pattern,
                "keys_deleted": deleted_keys
            }
            
        except Exception as e:
            span.set_attribute("error", str(e))
            logger.error(f"❌ Error limpiando caché: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
