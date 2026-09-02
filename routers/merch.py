from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from auth import CurrentUser
import models
from schemas import (
    MerchItemCreate,
    MerchItemUpdate,
    MerchItemResponse,
    MerchVariantCreate,
    MerchVariantUpdate,
    MerchVariantResponse,
    MerchReservationResponse,
    MerchReservationUpdate,
    ImageUploadRequest,
    ImageUploadResponse,
)
from storage import build_merch_image_key, build_public_url, generate_presigned_upload, delete_object

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]

async def _next_position(db: DbSession, user_id: int) -> int:
    result = await db.execute(
        select(func.max(models.MerchItem.position)).where(models.MerchItem.user_id == user_id)
    )
    max_position = result.scalar()
    return (max_position + 1) if max_position is not None else 0

async def _get_owned_item(item_id: int, db: DbSession, current_user: models.User) -> models.MerchItem:
    result = await db.execute(
        select(models.MerchItem)
        .where(models.MerchItem.id == item_id)
        .options(selectinload(models.MerchItem.variants))
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merch item not found")
    if item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this item")
    return item

async def _get_owned_variant(
    item: models.MerchItem, variant_id: int, db: DbSession
) -> models.MerchVariant:
    result = await db.execute(
        select(models.MerchVariant).where(
            models.MerchVariant.id == variant_id, models.MerchVariant.merch_item_id == item.id
        )
    )
    variant = result.scalars().first()
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
    return variant

def _validate_variant_for_item(item: models.MerchItem, size: models.MerchSize | None) -> None:
    if item.type == models.MerchType.clothing and size is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Clothing items require a size")
    if item.type == models.MerchType.misc:
        if size is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Misc items cannot have a size")
        if item.variants:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Misc items can only have one stock entry")
    if size is not None and any(variant.size == size for variant in item.variants):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Variant already exists for this size")

@router.post("/upload-url", response_model=ImageUploadResponse)
async def create_merch_image_upload_url(payload: ImageUploadRequest, current_user: CurrentUser):
    key = build_merch_image_key(current_user.slug, payload.content_type)
    presigned = generate_presigned_upload(key, payload.content_type)
    return ImageUploadResponse(
        upload_url=presigned["url"],
        fields=presigned["fields"],
        key=key,
        public_url=build_public_url(key),
    )

@router.get("", response_model=list[MerchItemResponse])
async def list_my_merch_items(db: DbSession, current_user: CurrentUser):
    result = await db.execute(
        select(models.MerchItem)
        .where(models.MerchItem.user_id == current_user.id)
        .options(selectinload(models.MerchItem.variants))
        .order_by(models.MerchItem.position)
    )
    return result.scalars().all()

@router.post("", response_model=MerchItemResponse, status_code=status.HTTP_201_CREATED)
async def create_merch_item(item_in: MerchItemCreate, db: DbSession, current_user: CurrentUser):
    data = item_in.model_dump()
    if data["position"] is None:
        data["position"] = await _next_position(db, current_user.id)
    item = models.MerchItem(**data, user_id=current_user.id)
    db.add(item)
    await db.commit()
    await db.refresh(item, attribute_names=["variants"])
    return item

@router.patch("/{item_id}", response_model=MerchItemResponse)
async def update_merch_item(item_id: int, item_in: MerchItemUpdate, db: DbSession, current_user: CurrentUser):
    item = await _get_owned_item(item_id, db, current_user)

    for field, value in item_in.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item, attribute_names=["variants"])
    return item

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_merch_item(item_id: int, db: DbSession, current_user: CurrentUser):
    item = await _get_owned_item(item_id, db, current_user)

    if item.image_key:
        delete_object(item.image_key)
    await db.delete(item)
    await db.commit()

@router.post("/{item_id}/variants", response_model=MerchVariantResponse, status_code=status.HTTP_201_CREATED)
async def create_merch_variant(
    item_id: int, variant_in: MerchVariantCreate, db: DbSession, current_user: CurrentUser
):
    item = await _get_owned_item(item_id, db, current_user)
    _validate_variant_for_item(item, variant_in.size)

    variant = models.MerchVariant(**variant_in.model_dump(), merch_item_id=item.id)
    db.add(variant)
    await db.commit()
    await db.refresh(variant)
    return variant

@router.patch("/{item_id}/variants/{variant_id}", response_model=MerchVariantResponse)
async def update_merch_variant(
    item_id: int, variant_id: int, variant_in: MerchVariantUpdate, db: DbSession, current_user: CurrentUser
):
    item = await _get_owned_item(item_id, db, current_user)
    variant = await _get_owned_variant(item, variant_id, db)

    for field, value in variant_in.model_dump(exclude_unset=True).items():
        setattr(variant, field, value)

    await db.commit()
    await db.refresh(variant)
    return variant

@router.delete("/{item_id}/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_merch_variant(item_id: int, variant_id: int, db: DbSession, current_user: CurrentUser):
    item = await _get_owned_item(item_id, db, current_user)
    variant = await _get_owned_variant(item, variant_id, db)

    await db.delete(variant)
    await db.commit()

@router.get("/reservations", response_model=list[MerchReservationResponse])
async def list_my_reservations(db: DbSession, current_user: CurrentUser):
    result = await db.execute(
        select(models.MerchReservation)
        .where(models.MerchReservation.user_id == current_user.id)
        .order_by(models.MerchReservation.created_at.desc())
    )
    return result.scalars().all()

@router.patch("/reservations/{reservation_id}", response_model=MerchReservationResponse)
async def update_reservation_status(
    reservation_id: int, update_in: MerchReservationUpdate, db: DbSession, current_user: CurrentUser
):
    result = await db.execute(
        select(models.MerchReservation).where(models.MerchReservation.id == reservation_id)
    )
    reservation = result.scalars().first()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    if reservation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this reservation")

    if update_in.status == models.ReservationStatus.cancelled and reservation.status != models.ReservationStatus.cancelled:
        variant_result = await db.execute(
            select(models.MerchVariant)
            .where(models.MerchVariant.id == reservation.merch_variant_id)
            .with_for_update()
        )
        variant = variant_result.scalars().first()
        if variant:
            variant.stock += reservation.quantity

    reservation.status = update_in.status
    await db.commit()
    await db.refresh(reservation)
    return reservation
