from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Drug Service API"
    database_url: str = "postgresql://drug_service:drug_service_local@localhost:5433/drug_service"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "drug_service_neo4j"
    opensearch_url: str = "http://localhost:9200"
    opensearch_index: str = "drug_service_text_v1"
    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://172.16.0.64:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


settings = Settings()
