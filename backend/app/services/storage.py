from minio import Minio
from minio.error import S3Error
import io
from app.core.config import settings


class StorageService:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            cls._ensure_bucket_once()
        return cls._instance

    @classmethod
    def _ensure_bucket_once(cls):
        try:
            if not cls._client.bucket_exists(settings.MINIO_BUCKET):
                cls._client.make_bucket(settings.MINIO_BUCKET)
        except S3Error:
            pass

    @property
    def client(self):
        return self._client

    async def upload_bytes(self, path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self._client.put_object(
            settings.MINIO_BUCKET,
            path,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return path

    async def download_bytes(self, path: str) -> bytes:
        response = self._client.get_object(settings.MINIO_BUCKET, path)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def delete(self, path: str):
        self._client.remove_object(settings.MINIO_BUCKET, path)

    def get_presigned_url(self, path: str, expires_seconds: int = 3600) -> str:
        from datetime import timedelta
        return self._client.presigned_get_object(
            settings.MINIO_BUCKET,
            path,
            expires=timedelta(seconds=expires_seconds),
        )
