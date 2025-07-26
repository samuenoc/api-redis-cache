from pydantic import BaseModel
from typing import Optional

class CacheStats(BaseModel):
    status: str
    total_keys: int
    catalog_keys: int
    memory_usage: Optional[str] = None
    uptime: Optional[str] = None