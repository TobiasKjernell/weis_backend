from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from auth import CurrentUser
import models
from schemas import GalleryImageCreate, GalleryImageUpdate, GalleryImageResponse, ImageUploadRequest, ImageUploadResponse
from storage import build_image_key, build_public_url, generate_presigned_upload, delete_object

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]

@router.post("/upload-url", response_model=ImageUploadResponse)
async def create_image_upload_url(payload: ImageUploadRequest, current_user: CurrentUser):
    key = build_image_key(current_user.slug, payload.content_type)
    presigned = generate_presigned_upload(key, payload.content_type)
    return ImageUploadResponse(
        upload_url=presigned["url"],
        fields=presigned["fields"],
        key=key,
        public_url=build_public_url(key),
    )

async def _next_position(db: DbSession, user_id: int) -> int:
    result = await db.execute(
        select(func.max(models.GalleryImage.position)).where(models.GalleryImage.user_id == user_id)
    )
    max_position = result.scalar()
    return (max_position + 1) if max_position is not None else 0

@router.get("", response_model=list[GalleryImageResponse])
async def list_my_images(db: DbSession, current_user: CurrentUser):
    result = await db.execute(
        select(models.GalleryImage)
        .where(models.GalleryImage.user_id == current_user.id)
        .order_by(models.GalleryImage.position)
    )
    return result.scalars().all()

@router.post("", response_model=GalleryImageResponse, status_code=status.HTTP_201_CREATED)
async def create_image(image_in: GalleryImageCreate, db: DbSession, current_user: CurrentUser):
    data = image_in.model_dump()
    if data["position"] is None:
        data["position"] = await _next_position(db, current_user.id)
    image = models.GalleryImage(**data, user_id=current_user.id)
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image

@router.patch("/{image_id}", response_model=GalleryImageResponse)
async def update_image(image_id: int, image_in: GalleryImageUpdate, db: DbSession, current_user: CurrentUser):
    result = await db.execute(select(models.GalleryImage).where(models.GalleryImage.id == image_id))
    image = result.scalars().first()

    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    if image.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this image")

    for field, value in image_in.model_dump(exclude_unset=True).items():
        setattr(image, field, value)

    await db.commit()
    await db.refresh(image)
    return image

@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(image_id: int, db: DbSession, current_user: CurrentUser):
    result = await db.execute(select(models.GalleryImage).where(models.GalleryImage.id == image_id))
    image = result.scalars().first()

    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    if image.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this image")

    delete_object(image.key)
    await db.delete(image)
    await db.commit()
