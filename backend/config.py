import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Настройки PostgreSQL
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "PAS"
    
    # Сборка URL для SQLAlchemy
    @property
    def DATABASE_URL(self) -> str:
        # --- ИЗМЕНЕНИЕ ---
        # Мы используем "postgresql+psycopg", чтобы SQLAlchemy
        # точно знал, что нужно использовать новый драйвер psycopg (v3).
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Настройки MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_SECURE: bool = False
    BUCKET_NAME: str = "images"
    
    # Настройки папки
    IMAGES_FOLDER: str = "skin_cancer_images"

    class Config:
        # Позволяет Pydantic читать .env-файлы
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
