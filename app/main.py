from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from dotenv import load_dotenv

# Importar controladores
from controllers import auth_controller, catalog_controller
from utils.database import get_db_connection
from utils.redis_cache import cache
from utils.telemetry import telemetry_service
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("steam-api")

# Crear instancia de FastAPI
app = FastAPI(
    title="Steam Data API", 
    version="1.0.0",
    description="API para datos de Steam con monitoreo completo y caché Redis"
)

# Instrumentar FastAPI
FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(auth_controller.router)
app.include_router(catalog_controller.router)


@app.get("/")
async def root():
    """Endpoint raíz"""
    telemetry_service.log_and_trace_request("root")
    with telemetry_service.tracer.start_as_current_span("root.processing") as span:
        span.set_attributes({
            "custom.message": "API is working",
            "custom.health": "ok"
        })
        logger.info("✅ Root endpoint procesado correctamente")
    return {"message": "Steam Data API funcionando! 🎮", "telemetry": "enabled", "cache": "redis"}

@app.get("/health")
async def health_check():
    """Health check completo"""
    telemetry_service.log_and_trace_request("health_check")
    
    with telemetry_service.tracer.start_as_current_span("health.database_check") as span:
        try:
            conn = get_db_connection()
            if conn:
                conn.close()
                span.set_attributes({
                    "database.status": "connected",
                    "health.check": "passed"
                })
                
                cache_stats = cache.get_cache_stats()
                
                logger.info("✅ Database health check passed")
                return {
                    "status": "healthy", 
                    "database": "connected", 
                    "telemetry": "active",
                    "cache": cache_stats
                }
            else:
                span.set_attributes({
                    "database.status": "disconnected",
                    "health.check": "failed"
                })
                logger.error("❌ Database health check failed")
                return {"status": "unhealthy", "database": "disconnected"}
        except Exception as e:
            span.set_attributes({
                "error": str(e),
                "health.check": "error"
            })
            logger.error(f"❌ Health check error: {e}")
            raise HTTPException(status_code=500, detail="Health check failed")

if __name__ == "__main__":
    logger.info("🚀 Starting Steam Data API with full telemetry and Redis cache...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")