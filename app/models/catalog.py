from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from decimal import Decimal

# Modelo para el ítem del catálogo
class CatalogItem(BaseModel):
    id: Optional[int] = Field(None, description="ID autogenerado del ítem")
    user_id: int = Field(..., description="ID del usuario asociado")
    game_title: str = Field(..., max_length=100, description="Título del juego")
    behavior_name: str = Field(..., max_length=50, description="Tipo de comportamiento")
    value: Decimal = Field(..., gt=0, description="Valor numérico del comportamiento")

    class Config:
        schema_extra = {
            "example": {
                "user_id": 12345,
                "game_title": "Portal 2",
                "behavior_name": "play",
                "value": "10.0",
            }
        }

# Modelo para la respuesta de creación de ítem 
class CatalogResponse(BaseModel):
    total: int
    message: str
    data: List[CatalogItem]
    cache_info: Optional[Dict[str, Any]] = None
    telemetry_info: Optional[Dict[str, Any]] = None

class CatalogItemCreationResponse(BaseModel):
    success: bool
    message: str
    item: CatalogItem
    admin_info: Dict[str, Any]
    cache_invalidation: Dict[str, Any]
    telemetry_info: Dict[str, Any]

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Item creado exitosamente",
                "item": {
                    "id": 200002,
                    "user_id": 12345,
                    "game_title": "Portal",
                    "behavior_name": "play",
                    "value": "1.00"
                },
                "admin_info": {
                    "admin_id": 8,
                    "admin_email": "admin@steamapi.com"
                },
                "cache_invalidation": {
                    "keys_deleted": 0
                },
                "telemetry_info": {
                    "duration_seconds": 1.056
                }
            }
        }
    }