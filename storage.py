import uuid
from functools import lru_cache

import boto3
from botocore.config import Config

from config import settings

CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

MAX_UPLOAD_BYTES = 2 * 1024 * 1024

@lru_cache
def get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        endpoint_url=f"https://s3.{settings.aws_region}.amazonaws.com",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key.get_secret_value(),
        config=Config(signature_version="s3v4"),
    )

def build_image_key(artist_slug: str, content_type: str) -> str:
    extension = CONTENT_TYPE_EXTENSIONS[content_type]
    return f"images/{artist_slug}/{uuid.uuid4().hex}{extension}"

def build_public_url(key: str) -> str:
    return f"https://{settings.cdn_domain}/{key}"

def generate_presigned_upload(key: str, content_type: str, expires_in: int = 300) -> dict:
    return get_s3_client().generate_presigned_post(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Fields={"Content-Type": content_type},
        Conditions=[
            {"Content-Type": content_type},
            ["content-length-range", 1, MAX_UPLOAD_BYTES],
        ],
        ExpiresIn=expires_in,
    )

def delete_object(key: str) -> None:
    get_s3_client().delete_object(Bucket=settings.s3_bucket_name, Key=key)
