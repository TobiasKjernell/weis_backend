from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from auth import verify_password
import models
from schemas import (
    ArtistPublic,
    YoutubeVideoResponse,
    TourDateResponse,
    GalleryImagePublic,
    MerchItemPublic,
    MerchReservationCreate,
    MerchReservationResponse,
    PressVerify,
)

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]

async def _get_artist_by_slug(slug: str, db: DbSession) -> models.User:
    result = await db.execute(
        select(models.User).where(models.User.slug == slug, models.User.is_admin == False)
    )
    artist = result.scalars().first()
    if not artist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artist not found")
    return artist

@router.get("", response_model=list[ArtistPublic])
async def list_artists(db: DbSession):
    result = await db.execute(
        select(models.User).where(models.User.is_admin == False).order_by(models.User.display_name)
    )
    return result.scalars().all()

@router.get("/{slug}", response_model=ArtistPublic)
async def get_artist(slug: str, db: DbSession):
    return await _get_artist_by_slug(slug, db)

@router.get("/{slug}/youtube", response_model=list[YoutubeVideoResponse])
async def list_artist_youtube_videos(slug: str, db: DbSession):
    artist = await _get_artist_by_slug(slug, db)
    result = await db.execute(
        select(models.YoutubeVideo)
        .where(models.YoutubeVideo.user_id == artist.id)
        .order_by(models.YoutubeVideo.position)
    )
    return result.scalars().all()

@router.get("/{slug}/tour-dates", response_model=list[TourDateResponse])
async def list_artist_tour_dates(slug: str, db: DbSession):
    artist = await _get_artist_by_slug(slug, db)
    result = await db.execute(
        select(models.TourDates)
        .where(models.TourDates.user_id == artist.id)
        .order_by(models.TourDates.date)
    )
    return result.scalars().all()

@router.get("/{slug}/images", response_model=list[GalleryImagePublic])
async def list_artist_images(slug: str, db: DbSession):
    artist = await _get_artist_by_slug(slug, db)
    result = await db.execute(
        select(models.GalleryImage)
        .where(models.GalleryImage.user_id == artist.id)
        .order_by(models.GalleryImage.position)
    )
    return result.scalars().all()

@router.get("/{slug}/merch", response_model=list[MerchItemPublic])
async def list_artist_merch(slug: str, db: DbSession):
    artist = await _get_artist_by_slug(slug, db)
    result = await db.execute(
        select(models.MerchItem)
        .where(models.MerchItem.user_id == artist.id, models.MerchItem.is_active == True)
        .options(selectinload(models.MerchItem.variants))
        .order_by(models.MerchItem.position)
    )
    return result.scalars().all()

@router.post(
    "/{slug}/merch/{item_id}/reserve",
    response_model=MerchReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def reserve_merch_item(slug: str, item_id: int, reservation_in: MerchReservationCreate, db: DbSession):
    artist = await _get_artist_by_slug(slug, db)

    item_result = await db.execute(
        select(models.MerchItem).where(
            models.MerchItem.id == item_id,
            models.MerchItem.user_id == artist.id,
            models.MerchItem.is_active == True,
        )
    )
    item = item_result.scalars().first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merch item not found")

    variant_result = await db.execute(
        select(models.MerchVariant)
        .where(
            models.MerchVariant.id == reservation_in.merch_variant_id,
            models.MerchVariant.merch_item_id == item.id,
        )
        .with_for_update()
    )
    variant = variant_result.scalars().first()
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")

    if variant.stock < reservation_in.quantity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Not enough stock available")

    variant.stock -= reservation_in.quantity
    reservation = models.MerchReservation(
        merch_variant_id=variant.id,
        user_id=artist.id,
        contact_email=reservation_in.contact_email,
        contact_instagram=reservation_in.contact_instagram,
        quantity=reservation_in.quantity,
        status=models.ReservationStatus.pending,
    )
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    return reservation

@router.post("/{slug}/press/verify", status_code=status.HTTP_204_NO_CONTENT)
async def verify_press_password(slug: str, data: PressVerify, db: DbSession):
    """Press-site gate: 204 if the password belongs to an unblocked label, else 401."""
    artist = await _get_artist_by_slug(slug, db)
    result = await db.execute(
        select(models.PressAccess).where(
            models.PressAccess.user_id == artist.id, models.PressAccess.is_blocked == False
        )
    )
    if not any(verify_password(data.password, e.password_hash) for e in result.scalars()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
