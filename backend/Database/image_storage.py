import io
from minio import Minio
from minio.error import S3Error
from config import settings
from datetime import timedelta

class MinioService:
    def __init__(self):
        try:
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            if not self.client.bucket_exists(settings.BUCKET_NAME):
                self.client.make_bucket(settings.BUCKET_NAME)
                print(f"Бакет '{settings.BUCKET_NAME}' создан.")
        except S3Error as e:
            print(f"Ошибка при инициализации MinIO: {e}")
            raise
    
    def upload_file(self, file_bytes: bytes, object_name: str, content_type: str = 'application/octet-stream') -> str:
        try:
            file_stream = io.BytesIO(file_bytes)
            file_size = len(file_bytes)
            
            self.client.put_object(
                settings.BUCKET_NAME,
                object_name,
                file_stream,
                file_size,
                content_type=content_type
            )
            print(f"✅ Файл '{object_name}' успешно загружен в MinIO.")
            return object_name
        except S3Error as err:
            print(f"Ошибка MinIO при загрузке: {err}")
            raise

    def get_presigned_url(self, object_name: str) -> str | None:
        """
        Генерирует временную (1 час) ссылку для GET-доступа к файлу.
        """
        try:
            url = self.client.presigned_get_object(
                settings.BUCKET_NAME,
                object_name,
                expires=timedelta(hours=1) # Ссылка будет активна 1 час
            )
            return url
        except S3Error as err:
            print(f"Ошибка MinIO при получении presigned URL: {err}")
            return None


minio_service = MinioService()
