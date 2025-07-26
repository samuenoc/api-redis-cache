import os
import logging
import time
from dotenv import load_dotenv
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from azure.monitor.opentelemetry.exporter import AzureMonitorMetricExporter

load_dotenv()
logger = logging.getLogger("telemetry")

class TelemetryService:
    def __init__(self):
        self.connection_string = os.getenv("APPINSIGHTS_CONNECTION_STRING")
        self.service_name = os.getenv("OTEL_SERVICE_NAME", "steam-api")
        self.service_version = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
        
        if not self.connection_string:
            logger.error("❌ APPINSIGHTS_CONNECTION_STRING no está configurado!")
            raise ValueError("Connection string de Application Insights requerido")
        
        self.tracer = None
        self.meter = None
        self.request_counter = None
        self.request_duration = None
        self.cache_hit_counter = None
        self.cache_miss_counter = None
        
        self._setup_telemetry()
    
    def _setup_telemetry(self):
        """Configurar OpenTelemetry con Azure Monitor"""
        logger.info(f"✅ Connection String configurado: {self.connection_string[:50]}...")
        
        # Configurar recurso
        resource = Resource.create(
            attributes={
                "service.name": self.service_name,
                "service.version": self.service_version,
                "service.instance.id": f"{self.service_name}-{os.getpid()}",
                "telemetry.sdk.name": "opentelemetry",
                "telemetry.sdk.language": "python",
                "cloud.provider": "azure"
            }
        )
        
        # Configurar trazas
        self._setup_traces(resource)
        
        # Configurar métricas
        self._setup_metrics(resource)
    
    def _setup_traces(self, resource):
        """Configurar trazas"""
        try:
            trace_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(trace_provider)
            self.tracer = trace.get_tracer(__name__)
            
            azure_exporter = AzureMonitorTraceExporter(
                connection_string=self.connection_string
            )
            
            span_processor = BatchSpanProcessor(
                azure_exporter,
                max_queue_size=2048,
                max_export_batch_size=512,
                export_timeout_millis=30000,
                schedule_delay_millis=5000
            )
            
            trace.get_tracer_provider().add_span_processor(span_processor)
            logger.info("✅ Azure Monitor Trace Exporter configurado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error configurando Azure Monitor: {e}")
            raise
    
    def _setup_metrics(self, resource):
        """Configurar métricas"""
        try:
            metric_reader = PeriodicExportingMetricReader(
                AzureMonitorMetricExporter(connection_string=self.connection_string),
                export_interval_millis=5000
            )
            metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))
            self.meter = metrics.get_meter(__name__)
            
            # Crear métricas personalizadas
            self.request_counter = self.meter.create_counter(
                name="http_requests_total",
                description="Total number of HTTP requests",
                unit="1"
            )
            
            self.request_duration = self.meter.create_histogram(
                name="http_request_duration_seconds",
                description="Duration of HTTP requests",
                unit="s"
            )
            
            self.cache_hit_counter = self.meter.create_counter(
                name="cache_hits_total",
                description="Total number of cache hits",
                unit="1"
            )
            
            self.cache_miss_counter = self.meter.create_counter(
                name="cache_misses_total",
                description="Total number of cache misses",
                unit="1"
            )
            
            logger.info("✅ Métricas de Azure Monitor configuradas")
            
        except Exception as e:
            logger.error(f"❌ Error configurando métricas: {e}")
    
    def log_and_trace_request(self, endpoint_name: str, **kwargs):
        """Log y crear span personalizado con atributos"""
        logger.info(f"📥 Request recibida en /{endpoint_name}")
        
        with self.tracer.start_as_current_span(
            f"custom.{endpoint_name}",
            attributes={
                "http.endpoint": endpoint_name,
                "custom.timestamp": str(time.time()),
                **kwargs
            }
        ) as span:
            self.request_counter.add(1, {"endpoint": endpoint_name})
            span.set_attribute("custom.processed", True)
            logger.info(f"✅ Span creado para {endpoint_name}")

# Instancia global de telemetría
telemetry_service = TelemetryService()