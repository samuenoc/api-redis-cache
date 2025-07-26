from datetime import datetime
from typing import Optional
import logging
import time

from fastapi import APIRouter, HTTPException, Query, Depends

from models.catalog import CatalogItem, CatalogItemCreationResponse, CatalogResponse
from utils.auth import require_admin, verify_custom_admin_token
from utils.database import get_db_connection
from utils.redis_cache import cache
from utils.telemetry import telemetry_service

logger = logging.getLogger("catalog_controller")
router = APIRouter(prefix="/catalog", tags=["Catálogo"])


@router.get("/", response_model=CatalogResponse)
async def get_catalog(
    game_title: Optional[str] = Query(None),
    behavior_name: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    limit: int = Query(10000, le=10000),
):
    """Obtener catálogo con filtros y caché"""
    start_time = time.time()
    telemetry_service.log_and_trace_request(
        "catalog", 
        game_title=game_title, 
        behavior_name=behavior_name, 
        user_id=user_id, 
        limit=limit
    )
    
    with telemetry_service.tracer.start_as_current_span("catalog.query_with_cache") as span:
        try:
            # Generar llave de caché
            query_params = {
                "game_title": game_title,
                "behavior_name": behavior_name,
                "user_id": user_id,
                "limit": limit
            }
            cache_key = cache.generate_cache_key("catalog", query_params)
            
            span.set_attributes({
                "query.game_title": game_title or "none",
                "query.behavior_name": behavior_name or "none",
                "query.user_id": user_id or "none",
                "query.limit": limit,
                "cache.key": cache_key
            })
            
            # Verificar caché
            cached_result = cache.get(cache_key)
            if cached_result:
                telemetry_service.cache_hit_counter.add(1, {"endpoint": "catalog"})
                duration = time.time() - start_time
                telemetry_service.request_duration.record(duration, {"endpoint": "catalog", "source": "cache"})
                
                cached_result["cache_info"] = {
                    "hit": True,
                    "key": cache_key,
                    "duration_seconds": round(duration, 3)
                }
                
                logger.info(f"✅ Catalog query from CACHE: {cached_result.get('total', 0)} results")
                return cached_result
            else:
                telemetry_service.cache_miss_counter.add(1, {"endpoint": "catalog"})
            
            # Consultar base de datos
            conn = get_db_connection()
            cur = conn.cursor()
            
            query = "SELECT * FROM user_behaviors WHERE 1=1"
            params = []
            
            if game_title:
                query += " AND game_title ILIKE %s"
                params.append(f"%{game_title}%")
            if behavior_name:
                query += " AND behavior_name = %s"
                params.append(behavior_name)
            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)
                
            query += f" ORDER BY id LIMIT {limit}"
            
            cur.execute(query, params)
            results = cur.fetchall()
            cur.close()
            conn.close()
            
            # Preparar respuesta
            response_data = {
                "total": len(results),
                "message": "Datos del catálogo obtenidos exitosamente",
                "filters_applied": {
                    "game_title": game_title,
                    "behavior_name": behavior_name,
                    "user_id": user_id,
                    "limit": limit
                },
                "data": [dict(row) for row in results]
            }
            
            # Guardar en caché
            cache_saved = cache.set(cache_key, response_data, ttl=3600)
            
            duration = time.time() - start_time
            telemetry_service.request_duration.record(duration, {"endpoint": "catalog", "source": "database"})
            
            response_data["telemetry_info"] = {
                "duration_seconds": round(duration, 3),
                "traced": True
            }
            response_data["cache_info"] = {
                "hit": False,
                "key": cache_key,
                "stored": cache_saved
            }
            
            logger.info(f"✅ Catalog query from DATABASE: {len(results)} results")
            return response_data
            
        except Exception as e:
            duration = time.time() - start_time
            span.set_attributes({
                "catalog.success": False,
                "catalog.duration": duration,
                "error": str(e)
            })
            logger.error(f"❌ Error en /catalog: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=CatalogItemCreationResponse)
async def create_catalog_item(
    item_data: CatalogItem,
    admin_data: dict = Depends(verify_custom_admin_token)
):
    """Crear nuevo item en el catálogo (solo para administradores)"""
    start_time = time.time()
    conn = None
    
    try:
        # Validación básica
        if not item_data.game_title or not item_data.behavior_name:
            raise HTTPException(
                status_code=400, 
                detail="game_title y behavior_name son requeridos"
            )

        # Insertar en DB
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO user_behaviors 
            (user_id, game_title, behavior_name, value)
            VALUES (%s, %s, %s, %s)
            RETURNING id, user_id, game_title, behavior_name, value
        """, (
            item_data.user_id,
            item_data.game_title,
            item_data.behavior_name,
            item_data.value,
        ))
        
        new_item = cur.fetchone()
        conn.commit()
        
        # Convertir a CatalogItem
        created_item = CatalogItem(
            id=new_item['id'],
            user_id=new_item['user_id'],
            game_title=new_item['game_title'],
            behavior_name=new_item['behavior_name'],
            value=new_item['value']
        )
        
        # Invalidar caché (con manejo seguro de errores)
        deleted_keys = 0
        try:
            if hasattr(cache, 'is_connected') and cache.is_connected():
                deleted_keys = cache.invalidate_catalog_cache(
                    game_title=item_data.game_title,
                    behavior_name=item_data.behavior_name,
                    user_id=item_data.user_id
                )
        except Exception as e:
            logger.error(f"Error al invalidar caché: {str(e)}")
        
        # Preparar respuesta
        return CatalogItemCreationResponse(
            success=True,
            message="Item creado exitosamente",
            item=created_item,
            admin_info={
                "admin_id": admin_data["user_id"],
                "admin_email": admin_data["email"]
            },
            cache_invalidation={
                "keys_deleted": deleted_keys
            },
            telemetry_info={
                "duration_seconds": round(time.time() - start_time, 3)
            }
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error creando item: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="Error interno al crear item"
        )
    finally:
        if conn:
            conn.close()