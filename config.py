from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    database_url: str
    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    frontend_url: str | None = None

    aws_access_key_id: str
    aws_secret_access_key: SecretStr
    aws_region: str
    s3_bucket_name: str
    cdn_domain: str

settings = Settings()
