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
    # A blank/misconfigured AWS_REGION fails here with a clear error instead
    # of silently producing a malformed endpoint. addressing_style="virtual"
    # is required too: boto3's generate_presigned_post omits the region from
    # the host under the default "auto" style, which makes S3 307-redirect
    # to the correct regional endpoint — and that redirect breaks the
    # browser's cross-origin POST (fetch can't carry a multipart/form-data
    # body through a cross-origin redirect and still satisfy CORS on the
    # second hop).
    if not settings.aws_region:
        raise RuntimeError("AWS_REGION is not configured")
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key.get_secret_value(),
        config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
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
