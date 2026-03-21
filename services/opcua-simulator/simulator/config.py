"""Configuration for OPC-UA Simulation Server."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Environment-based configuration."""

    # OPC-UA Server
    opcua_endpoint: str = "opc.tcp://0.0.0.0:4840/forgelink/"
    opcua_server_name: str = "ForgeLink Steel Plant Simulator"
    opcua_namespace: str = "urn:forgelink:steel-plant"

    # Redis connection (for Django communication)
    redis_url: str = "redis://localhost:6379/2"
    redis_channel: str = "forgelink:opcua:values"

    # Django API (for initial device sync)
    django_api_url: str = "http://localhost:8000"

    # Plant configuration
    plant_name: str = "steel-plant-kigali"

    # Logging
    log_level: str = "INFO"

    # Health check
    health_port: int = 8081

    # Metrics
    metrics_port: int = 9091

    class Config:
        env_prefix = "OPCUA_"
        env_file = ".env"
        extra = "ignore"


settings = Settings()
