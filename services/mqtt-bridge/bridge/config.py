"""Configuration for ForgeLink MQTT Bridge."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Environment-based configuration."""

    # EMQX
    emqx_host: str = "localhost"
    emqx_port: int = 1883
    emqx_mqtt_username: str = "bridge"
    emqx_mqtt_password: str = "bridge_dev_password"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_partitions: int = 3

    # Topics
    mqtt_subscribe_topic: str = "forgelink/#"

    # Logging
    log_level: str = "INFO"

    # Metrics
    metrics_port: int = 8000

    class Config:
        env_prefix = ""
        env_file = ".env"
        extra = "ignore"


settings = Settings()
