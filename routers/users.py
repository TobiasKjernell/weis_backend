from fastapi import APIRouter, Depends, status, HTTPException
from schemas import (
    Token,
    ArtistCreate,
    ArtistAdminResponse,
    YoutubeVideoCreate,
    YoutubeVideoUpdate,
    YoutubeVideoResponse,
    TourDateCreate,
    TourDateUpdate,
    TourDateResponse,
    GalleryImageCreate,
    GalleryImageUpdate,
    GalleryImageResponse,
    ImageUploadRequest,
    ImageUploadResponse,
)
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from database import get_db
from auth import create_access_token, verify_password, hash_password, CurrentAdmin
from sqlalchemy import func, select
import models
from storage import build_image_key, build_public_url, generate_presigned_upload, delete_object

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]

async def _get_artist_by_slug_for_admin(slug: str, db: DbSession) -> models.User:
    result = await db.execute(
        select(models.User).where(models.User.slug == slug, models.User.is_admin == False)
    )
    artist = result.scalars().first()
    if not artist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artist not found")
    return artist

async def _next_youtube_position(db: DbSession, user_id: int) -> int:
    result = await db.execute(
        select(func.max(models.YoutubeVideo.position)).where(models.YoutubeVideo.user_id == user_id)
    )
    max_position = result.scalar()
    return (max_position + 1) if max_position is not None else 0

async def _next_image_position(db: DbSession, user_id: int) -> int:
    result = await db.execute(
        select(func.max(models.GalleryImage.position)).where(models.GalleryImage.user_id == user_id)
    )
    max_position = result.scalar()
    return (max_position + 1) if max_position is not None else 0

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    result = await db.execute(select(models.User).where(models.User.username == form_data.username.lower()))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})

    token = create_access_token(data={"sub": str(user.username)})

    return Token(access_token=token, token_type="bearer")

@router.post("", response_model=ArtistAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_artist(artist_in: ArtistCreate, db: DbSession, _admin: CurrentAdmin):
    new_artist = models.User(
        username=artist_in.username,
        password_hash=hash_password(artist_in.password),
        slug=artist_in.slug,
        display_name=artist_in.display_name,
        is_admin=False,
    )
    db.add(new_artist)
    try:
        await db.commit()
    except IntegrityError as err:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or slug already taken") from err

    await db.refresh(new_artist)
    return new_artist

@router.get("", response_model=list[ArtistAdminResponse])
async def list_artists_admin(db: DbSession, _admin: CurrentAdmin):
    result = await db.execute(select(models.User).order_by(models.User.display_name))
    return result.scalars().all()

@router.get("/{slug}", response_model=ArtistAdminResponse)
async def get_artist_admin(slug: str, db: DbSession, _admin: CurrentAdmin):
    result = await db.execute(select(models.User).where(models.User.slug == slug))
    artist = result.scalars().first()
    if not artist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artist not found")
    return artist

# --- Admin-on-behalf-of-artist content management ---
# The artist-facing /api/youtube and /api/tour-dates routes only ever act on
# the token's own user_id. These mirror them so an admin can help an artist
# manage their content without needing that artist's credentials.

@router.get("/{slug}/youtube", response_model=list[YoutubeVideoResponse])
async def admin_list_artist_youtube(slug: str, db: DbSession, _admin: CurrentAdmin):
    artist = await _get_artist_by_slug_for_admin(slug, db)
    result = await db.execute(
        select(models.YoutubeVideo)
        .where(models.YoutubeVideo.user_id == artist.id)
        .order_by(models.YoutubeVideo.position)
    )
    return result.scalars().all()

@router.post("/{slug}/youtube", response_model=YoutubeVideoResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_artist_youtube(slug: str, video_in: YoutubeVideoCreate, db: DbSession, _admin: CurrentAdmin):
    artist = await _get_artist_by_slug_for_admin(slug, db)
    data = video_in.model_dump()
    if data["position"] is None:
        data["position"] = await _next_youtube_position(db, artist.id)
    video = models.YoutubeVideo(**data, user_id=artist.id)
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video

@router.patch("/{slug}/youtube/{video_id}", response_model=YoutubeVideoResponse)
async def admin_update_artist_youtube(
    slug: str, video_id: int, video_in: YoutubeVideoUpdate, db: DbSession, _admin: CurrentAdmin
):
    artist = await _get_artist_by_slug_for_admin(slug, db)
    result = await db.execute(select(models.YoutubeVideo).where(models.YoutubeVideo.id == video_id))
    video = result.scalars().first()

    if not video or video.user_id != artist.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    for field, value in video_in.model_dump(exclude_unset=True).items():
        setattr(video, field, value)

    await db.commit()
    await db.refresh(video)
    return video

@router.delete("/{slug}/youtube/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_artist_youtube(slug: str, video_id: int, db: DbSession, _admin: CurrentAdmin):
    artist = await _get_artist_by_slug_for_admin(slug, db)
    result = await db.execute(select(models.YoutubeVideo).where(models.YoutubeVideo.id == video_id))
    video = result.scalars().first()

    if not video or video.user_id != artist.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    await db.delete(video)
    await db.commit()

@router.get("/{slug}/tour-dates", response_model=list[TourDateResponse])
async def admin_list_artist_tour_dates(slug: str, db: DbSession, _admin: CurrentAdmin):
    artist = await _get_artist_by_slug_for_admin(slug, db)
    result = await db.execute(
        select(models.TourDates)
        .where(models.TourDates.user_id == artist.id)
        .order_by(models.TourDates.date)
    )
    return result.scalars().all()

@router.post("/{slug}/tour-dates", response_model=TourDateResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_artist_tour_date(slug: str, tour_date_in: TourDateCreate, db: DbSession, _admin: CurrentAdmin):
    artist = await _get_artist_by_slug_for_admin(slug, db)
    tour_date = models.TourDates(**tour_date_in.model_dump(), user_id=artist.id)
    db.add(tour_date)
    await db.commit()
    await db.refresh(tour_date)
    return tour_date

@router.patch("/{slug}/tour-dates/{tour_date_id}", response_model=TourDateResponse)
async def admin_update_artist_tour_date(
    slug: str, tour_date_id: int, tour_date_in: TourDateUpdate, db: DbSession, _admin: CurrentAdmin
):
    artist = await _get_artist_by_slug_for_admin(slug, db)
    result = await db.execute(select(models.TourDates).where(models.TourDates.id == tour_date_id))
    tour_date = result.scalars().first()

    if not tour_date or tour_date.user_id != artist.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour date not found")

    for field, value in tour_date_in.model_dump(exclude_unset=True).items():
        setattr(tour_date, field, value)

    await db.commit()
    await db.refresh(tour_date)
    return tour_date

@router.delete("/{slug}/tour-dates/{tour_date_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_artist_tour_date(slug: str, tour_date_id: int, db: DbSession, _admin: CurrentAdmin):
    artist = await _get_artist_by_slug_for_admin(slug, db)
    result = await db.execute(select(models.TourDates).where(models.TourDates.id == tour_date_id))
    tour_date = result.scalars().first()

    if not tour_date or tour_date.user_id != artist.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour date not found")

    await db.delete(tour_date)
    await db.commit()

@router.post("/{slug}/images/upload-url", response_model=ImageUploadResponse)
async def admin_create_artist_image_upload_url(
    slug: str, payload: ImageUploadRequest, db: DbSession, _admin: CurrentAdmin
):
    artist = await _get_artist_by_slug_for_admin(slug, db)
    key = build_image_key(artist.slug, payload.content_type)
    presigned = generate_presigned_upload(key, payload.content_type)
    return ImageUploadResponse(
        upload_url=presigned["url"],
        fields=presigned["fields"],
        key=key,
        public_url=build_public_url(key),
    )

@router.get("/{slug}/images", response_model=list[GalleryImageResponse])
async def admin_list_artist_images(slug: str, db: DbSession, _admin: CurrentAdmin):
    artist = await _get_artist_by_slug_for_admin(slug, db)
    result = await db.execute(
        select(models.GalleryImage)
        .where(models.GalleryImage.user_id == artist.id)
        .order_by(models.GalleryImage.position)
    )
    return result.scalars().all()

@router.post("/{slug}/images", response_model=GalleryImageResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_artist_image(slug: str, image_in: GalleryImageCreate, db: DbSession, _admin: CurrentAdmin):
    artist = await _get_artist_by_slug_for_admin(slug, db)
    data = image_in.model_dump()
    if data["position"] is None:
        data["position"] = await _next_image_position(db, artist.id)
    image = models.GalleryImage(**data, user_id=artist.id)
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image

@router.patch("/{slug}/images/{image_id}", response_model=GalleryImageResponse)
async def admin_update_artist_image(
    slug: str, image_id: int, image_in: GalleryImageUpdate, db: DbSession, _admin: CurrentAdmin
):
    artist = await _get_artist_by_slug_for_admin(slug, db)
    result = await db.execute(select(models.GalleryImage).where(models.GalleryImage.id == image_id))
    image = result.scalars().first()

    if not image or image.user_id != artist.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    for field, value in image_in.model_dump(exclude_unset=True).items():
        setattr(image, field, value)

    await db.commit()
    await db.refresh(image)
    return image

@router.delete("/{slug}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_artist_image(slug: str, image_id: int, db: DbSession, _admin: CurrentAdmin):
    artist = await _get_artist_by_slug_for_admin(slug, db)
    result = await db.execute(select(models.GalleryImage).where(models.GalleryImage.id == image_id))
    image = result.scalars().first()

    if not image or image.user_id != artist.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    delete_object(image.key)
    await db.delete(image)
    await db.commit()
