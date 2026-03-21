"""Configuration for Edge Gateway."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Environment-based configuration."""

    # OPC-UA Server connection
    opcua_endpoint: str = "opc.tcp://localhost:4840/forgelink/"
    opcua_namespace: str = "urn:forgelink:steel-plant"
    opcua_reconnect_interval: int = 5  # seconds

    # MQTT Broker connection
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str = "bridge"
    mqtt_password: str = "bridge_dev_password"
    mqtt_client_id: str = "forgelink-edge-gateway"
    mqtt_reconnect_interval: int = 5  # seconds

    # UNS Configuration
    uns_root: str = "forgelink"
    plant_name: str = "steel-plant-kigali"

    # Subscription settings
    subscription_interval: int = 1000  # milliseconds
    dead_band: float = 0.0  # absolute dead band
    queue_size: int = 10

    # Buffering (for handling disconnects)
    buffer_size: int = 10000  # max messages to buffer
    buffer_flush_interval: int = 100  # milliseconds

    # Logging
    log_level: str = "INFO"

    # Health check
    health_port: int = 8082

    # Metrics
    metrics_port: int = 9092

    class Config:
        env_prefix = "EDGE_"
        env_file = ".env"
        extra = "ignore"


settings = Settings()
