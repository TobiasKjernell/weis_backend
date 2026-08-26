from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
import models
from schemas import ArtistPublic, YoutubeVideoResponse, TourDateResponse

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]

async def _get_artist_by_slug(slug: str, db: DbSession) -> models.User:
    result = await db.execute(select(models.User).where(models.User.slug == slug))
    artist = result.scalars().first()
    if not artist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artist not found")
    return artist

@router.get("", response_model=list[ArtistPublic])
async def list_artists(db: DbSession):
    result = await db.execute(select(models.User).order_by(models.User.display_name))
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
